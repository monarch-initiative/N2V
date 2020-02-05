import sys
import numpy as np
from sklearn import metrics
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_curve, roc_auc_score, average_precision_score
import logging
import os


handler = logging.handlers.WatchedFileHandler(os.environ.get("LOGFILE", "link_prediction.log"))
formatter = logging.Formatter('%(asctime)s - %(levelname)s -%(filename)s:%(lineno)d - %(message)s')
handler.setFormatter(formatter)
log = logging.getLogger()
log.setLevel(os.environ.get("LOGLEVEL", "DEBUG"))
log.addHandler(handler)

class LinkPrediction:
    def __init__(self, pos_train_graph, pos_test_graph, neg_train_graph, neg_test_graph,
                 embedded_train_graph_path, edge_embedding_method):
        """
        Set up for predicting links from results of node2vec analysis
        :param pos_train_graph: The training graph
        :param pos_test_graph:  Graph of links that we want to predict
        :param neg_train_graph: Graph of non-existence links in training graph
        :param neg_test_graph: Graph of non-existence links that we want to predict as negative edges
        :param embedded_train_graph_path: The file produced by word2vec with the nodes embedded as vectors
        :param edge_embedding_method: The method to embed edges. It can be "hadamard", "average", "weightedL1" or "weightedL2"
        """
        self.pos_train_edges = pos_train_graph.edges()
        self.pos_test_edges = pos_test_graph.edges()
        self.neg_train_edges = neg_train_graph.edges()
        self.neg_test_edges = neg_test_graph.edges()
        self.train_nodes = pos_train_graph.nodes()
        self.test_nodes = pos_test_graph.nodes()
        self.embedded_train_graph = embedded_train_graph_path
        self.map_node_vector = {}
        self.read_embeddings()
        self.edge_embedding_method = edge_embedding_method

    def read_embeddings(self):
        """
        reading the embeddings generated by the training graph
        :return:
        """
        n_lines = 0
        map_node_vector = {}  # reading the embedded graph to a map, key:node, value:vector
        with open(self.embedded_train_graph, 'r') as f:
            #next(f)#skip the header which contains 2 integers; number of nodes and dimension
            for line in f:
                fields = line.split('\t') #the format of each line: node v_1 v_2 ... v_d where v_i's are elements of
                # the array corresponding to the embedding of the node
                embe_vec = [float(i) for i in fields[1:]]
                map_node_vector.update({fields[0]: embe_vec})#map each node to its corresponding vector
                n_lines += 1
        f.close()
        self.map_node_vector = map_node_vector
        log.debug("Finished ingesting {} lines (vectors) from {}".format(n_lines, self.embedded_train_graph))


    def predict_links(self):
        pos_train_edge_embs = self.transform(edge_list=self.pos_train_edges, node2vector_map=self.map_node_vector)
        neg_train_edge_embs = self.transform(edge_list=self.neg_train_edges, node2vector_map=self.map_node_vector)
        #print(len(true_train_edge_embs),len(false_train_edge_embs))
        train_edge_embs = np.concatenate([pos_train_edge_embs, neg_train_edge_embs])
        # Create train-set edge labels: 1 = true edge, 0 = false edge
        train_edge_labels = np.concatenate([np.ones(len(pos_train_edge_embs)), np.zeros(len(neg_train_edge_embs))])

        # Test-set edge embeddings, labels
        pos_test_edge_embs = self.transform(edge_list=self.pos_test_edges, node2vector_map=self.map_node_vector)
        neg_test_edge_embs = self.transform(edge_list=self.neg_test_edges, node2vector_map=self.map_node_vector)
        test_edge_embs = np.concatenate([pos_test_edge_embs, neg_test_edge_embs])
        # Create test-set edge labels: 1 = true edge, 0 = false edge
        test_edge_labels = np.concatenate([np.ones(len(pos_test_edge_embs)), np.zeros(len(neg_test_edge_embs))])
        log.debug('get test edge labels')

        #log.debug("Total nodes: {}".format(self.train_edges.number_of_nodes()))
        log.debug("Total edges of training graph: {}".format(len(self.pos_train_edges)))
        log.debug("Training edges (negative): {}".format(len(neg_train_edge_embs)))
        log.debug("Test edges (positive): {}".format(len(self.pos_test_edges)))
        log.debug("Test edges (negative): {}".format(len(neg_test_edge_embs)))
        log.debug('logistic regression')
        # Train logistic regression classifier on train-set edge embeddings
        edge_classifier = LogisticRegression()
        edge_classifier.fit(train_edge_embs, train_edge_labels)

        self.predictions = edge_classifier.predict(test_edge_embs)
        self.confusion_matrix = metrics.confusion_matrix(test_edge_labels, self.predictions)

        # Predicted edge scores: probability of being of class "1" (real edge)
        test_preds = edge_classifier.predict_proba(test_edge_embs)[:, 1]
        fpr, tpr, _ = roc_curve(test_edge_labels, test_preds)

        self.test_roc = roc_auc_score(test_edge_labels, test_preds)#get the auc score
        self.test_average_precision = average_precision_score(test_edge_labels, test_preds)

    def output_Logistic_Reg_results(self):
        """
        The method prints some metrics of the performance of the logistic regression classifier. including accuracy, specificity and sensitivity
        :param predictions: prediction results of the logistic regression
        :param confusion_matrix:  confusion_matrix[0, 0]: True negatives, confusion_matrix[0, 1]: False positives,
        confusion_matrix[1, 1]: True positives and confusion_matrix[1, 0]: False negatives
        :param test_roc: AUC score
        :param test_average_precision: Average precision
        :return:
         """
        confusion_matrix = self.confusion_matrix
        total = sum(sum(confusion_matrix))
        accuracy = (confusion_matrix[0, 0] + confusion_matrix[1, 1]) * (1.0) / total
        specificity = confusion_matrix[0, 0] * (1.0) / (confusion_matrix[0, 0] + confusion_matrix[0, 1]) * (1.0)
        sensitivity = confusion_matrix[1, 1] * (1.0) / (confusion_matrix[1, 0] + confusion_matrix[1, 1]) * (1.0)

        log.debug("predictions: {}".format(str(self.predictions)))
        log.debug("confusion matrix: {}".format(str(confusion_matrix)))
        log.debug('Accuracy : {}'.format(accuracy))
        log.debug('Specificity : {}'.format(specificity))
        log.debug('Sensitivity : {}'.format(sensitivity))
        log.debug("node2vec Test ROC score: {} ".format(str(self.test_roc)))
        log.debug("node2vec Test AP score: {} ".format(str(self.test_average_precision)))

    def transform(self,edge_list, node2vector_map):
        """
        This method finds embedding for edges of the graph. There are 4 ways to calculate edge embedding: Hadamard, Average, Weighted L1 and Weighted L2
        :param edge_list:
        :param node2vector_map: key:node, value: embedded vector
        :param size_limit: Maximum number of edges that are embedded
        :return: list of embedded edges
        """
        embs = []
        edge_embedding_method = self.edge_embedding_method
        for edge in edge_list:
            node1 = edge[0]
            node2 = edge[1]
            emb1 = node2vector_map[node1]
            emb2 = node2vector_map[node2]
            if edge_embedding_method == "hadamard":
                # Perform a Hadamard transform on the node embeddings.
                # This is a dot product of the node embedding for the two nodes that
                # belong to each edge
                edge_emb = np.multiply(emb1, emb2)
            elif edge_embedding_method == "average":
                # Perform a Average transform on the node embeddings.
                # This is a elementwise average of the node embedding for the two nodes that
                # belong to each edge
                edge_emb = np.add(emb1, emb2) / 2
            elif edge_embedding_method == "weightedL1":
                # Perform weightedL1 transform on the node embeddings.
                # WeightedL1 calculates the absolute value of difference of each element of the two nodes that
                # belong to each edge
                edge_emb = abs(emb1 - emb2)
            elif edge_embedding_method == "weightedL2":
                # Perform weightedL2 transform on the node embeddings.
                # WeightedL2 calculates the square of difference of each element of the two nodes that
                # belong to each edge
                edge_emb = np.power((emb1 - emb2), 2)
            else:
                log.error("You need to enter hadamard, average, weightedL1, weightedL2")
                sys.exit(1)
            embs.append(edge_emb)
        embs = np.array(embs)
        return embs

    def output_diagnostics_to_logfile(self):
        LinkPrediction.log_edge_node_information(self.pos_train_edges, "true_training")
        LinkPrediction.log_edge_node_information(self.pos_test_edges, "true_test")

    @staticmethod
    def log_edge_node_information(edge_list, group):#TODO:modify it for the homogenous graph
        """
        log the number of nodes and edges of each type of the graph
        :param edge_list: e.g.,  [('1','7), ('88','22'),...], either training or test
        :return:
        """
        num_gene_gene = 0
        num_gene_dis = 0
        num_gene_prot = 0
        num_prot_prot = 0
        num_prot_dis = 0
        num_dis_dis = 0
        num_gene = 0
        num_prot = 0
        num_dis = 0
        nodes = set()
        for edge in edge_list:
            if (edge[0].startswith("g") and edge[1].startswith("g")):
                num_gene_gene += 1
            elif ((edge[0].startswith("g") and edge[1].startswith("d")) or
                  (edge[0].startswith("d") and edge[1].startswith("g"))):
                num_gene_dis += 1
            elif ((edge[0].startswith("g") and edge[1].startswith("p")) or
                  (edge[0].startswith("p") and edge[1].startswith("g"))):
                num_gene_prot += 1
            elif edge[0].startswith("p") and edge[1].startswith("p"):
                num_prot_prot += 1
            elif (edge[0].startswith("p") and edge[1].startswith("d")) or (
                    edge[0].startswith("d") and edge[1].startswith("p")):
                num_prot_dis += 1
            elif edge[0].startswith("d") and edge[1].startswith("d"):
                num_dis_dis += 1
            nodes.add(edge[0])
            nodes.add(edge[1])
        for node in nodes:
            if node.startswith("g"):
                num_gene += 1
            elif node.startswith("p"):
                num_prot += 1
            elif node.startswith("d"):
                num_dis += 1
        log.debug("##### edge/node diagnostics for {} #####".format(group))
        log.debug("{}: number of gene-gene edges : {}".format(group, num_gene_gene))
        log.debug("{}: number of gene-dis edges : {}".format(group, num_gene_dis))
        log.debug("{}: number of gene-prot edges : {}".format(group, num_gene_prot))
        log.debug("{}: number of prot_prot edges : {}".format(group, num_prot_prot))
        log.debug("{}: number of prot_dis edges : {}".format(group, num_prot_dis))
        log.debug("{}: number of dis_dis edges : {}".format(group, num_dis_dis))
        log.debug("{}: number of gene nodes : {}".format(group, num_gene))
        log.debug("{}: number of protein nodes : {}".format(group, num_prot))
        log.debug("{}: number of disease nodes : {}".format(group, num_dis))
        log.debug("##########")