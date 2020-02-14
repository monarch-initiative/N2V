import xn2v
from xn2v import CSFGraph
from xn2v.word2vec import SkipGramWord2Vec
from xn2v.word2vec import ContinuousBagOfWordsWord2Vec
import os

dir = '/home/peter/GIT/node2vec-eval'
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
training_file = os.path.join(current_dir,'tests/data/ppismall/pos_train_edges') # os.path.join(dir, 'pos_train_edges')

g = CSFGraph(training_file)


p = 1
q = 1
gamma = 1
useGamma = False
graph = xn2v.hetnode2vec.N2vGraph(g, p, q, gamma, useGamma)

walk_length = 80
num_walks = 10
walks = graph.simulate_walks(num_walks, walk_length)
dimensions = 128
window_size = 10
workers = 8


worddictionary = g.get_node_to_index_map()
reverse_worddictionary = g.get_index_to_node_map()

model = SkipGramWord2Vec(walks, worddictionary=worddictionary, reverse_worddictionary=reverse_worddictionary, num_steps=100)
model.train(display_step=2)


print("And now let's try CBOW")

model = ContinuousBagOfWordsWord2Vec(walks, worddictionary=worddictionary, reverse_worddictionary=reverse_worddictionary, num_steps=100)
model.train(display_step=2)










