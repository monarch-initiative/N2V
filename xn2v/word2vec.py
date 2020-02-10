import random
import math
import numpy as np
import tensorflow as tf
import collections
from xn2v.w2v.cbow_list_batcher import CBOWBatcherListOfLists


class Word2Vec:
    """Superclass of all of the word2vec family algorithms.

    Attributes:
        word2id: A dictionary where the keys are nodes/words and values are integers that represent those nodes/words.
        id2word: A dictionary where the keys are integers and values are the nodes represented by the integers.
        data: A list or list of lists (if sentences or paths from node2vec).
        learning_rate: A float between 0 and 1 that controls how fast the model learns to solve the problem.
        batch_size: The size of each "batch" or slice of the data to sample when training the model.
        num_steps: The number of epochs to run when training the model.
        display_step: An integer that is used to determine the number of steps to display.
        eval_step: This attribute stores the total number of iterations to run during training.
        embedding_size: Dimension of embedded vectors.
        max_vocabulary_size: Maximum number of words. Total number of different words in the vocabulary.
        min_occurrence: Minimum number of times a word needs to appear to be included.
        skip_window: How many words to consider left and right.
        num_skips: How many times to reuse an input to generate a label.
        num_sampled: Number of negative examples to sample.
        display: An integer of the number of words to display.
        display_examples: A list containing examples from the vocabulary the user wishes to display.
        vocabulary_size: An integer storing the total number of unique words in the vocabulary.
        embedding: A 2D tensor with shape (samples, sequence_length), where each entry is a sequence of integers.
    """

    def __init__(self, data: list, worddictionary: dict, reverse_worddictionary: dict, learning_rate: float = 0.1,
                 batch_size: int = 128, num_steps: int = 3000000, embedding_size: int = 200,
                 max_vocabulary_size: int = 50000, min_occurrence: int = 1,  # default=2
                 skip_window: int = 3, num_skips: int = 2, num_sampled: int = 7,  # default=64
                 display: int = None):

        self.word2id = worddictionary
        self.id2word = reverse_worddictionary
        self.data = data
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.num_steps = num_steps
        self.display_step = 2000
        self.eval_step = 2000
        self.embedding_size = embedding_size
        self.max_vocabulary_size = max_vocabulary_size
        self.min_occurrence = min_occurrence
        self.skip_window = skip_window
        self.num_skips = num_skips
        self.num_sampled = num_sampled
        self.display = display
        self.display_examples: list = []
        self.vocabulary_size = None
        self.embedding = None

    def add_display_words(self, count: list, num: int = 5):
        """Creates a list of display nodes/words by obtaining a random sample of 'num' nodes/words from the full
        sample.

        If the argument 'display' is not None, then we expect that the user has passed an integer amount of words
        that are to be displayed together with their nearest neighbors, as defined by the word2vec algorithm. It is
        important to note that display is a costly operation. Up to 16 nodes/words are permitted. If a user asks for
        more than 16, a random validation set of 'num' nodes/words, that includes common and uncommon nodes/words, is
        selected from a 'valid_window' of 50 nodes/words.

        Args:
            count: A list of tuples (key:word, value:int).
            num: An integer representing the number of words to sample.

        Returns:
            None.
        """

        if not isinstance(count, list):
            self.display = None
            # print("[WARNING] add_display_words requires a list of tuples with k:word v:int (count)")
            # return
            raise Exception('[WARNING] add_display_words requires a list of tuples with key:word, value:int (count)')

        if num > 16:
            print('[WARNING] maximum of 16 display words allowed (you passed {num_words})'.format(num_words=num))
            num = 16

        # pick a random validation set of 'num' words to sample
        valid_window = 50
        valid_examples = np.array(random.sample(range(2, valid_window), num))

        # sample less common words - choose 'num' points randomly from the first 'valid_window' after element 1000
        self.display_examples = np.append(valid_examples, random.sample(range(1000, 1000 + valid_window), num), axis=0)

        return None

    def calculate_vocabulary_size(self):
        """Calculates the vocabulary size for the input data, which is a list of words (i.e. from a text),
        or list of lists (i.e. from a collection of sentences or random walks).

        Returns:
            None.
        """

        if any(isinstance(el, list) for el in self.data):
            flat_list = [item for sublist in self.data for item in sublist]
            self.vocabulary_size = min(self.max_vocabulary_size, len(set(flat_list)) + 1)
            print('Vocabulary size (list of lists) is {vocab_size}'.format(vocab_size=self.vocabulary_size))
        else:
            self.vocabulary_size = min(self.max_vocabulary_size, len(set(self.data)) + 1)
            print('Vocabulary size (flat) is {vocab_size}'.format(vocab_size=self.vocabulary_size))

    def write_embeddings(self, outfilename: str):
        """Writes embedding data to a local directory. Data is written out in the following format, which is consistent
        with current standards:
            'ENSP00000371067' 0.6698335 , -0.83192813, -0.3676057 , ...,  0.9241863 , -2.1407487 , -0.6607736
            'ENSP00000374213' -0.6342755 , -2.0504158 , -1.169239  , ..., -0.8034669 , 0.5925971 , -0.00864262

        Args:
            outfilename: A string containing a filepath for writing embedding data.

        Returns:
            None.
        """

        if not self.embedding:
            raise ValueError('No embedding data found (i.e. self.embedding is None)')
        if not self.id2word:
            raise ValueError('No node/word dictionary data found (i.e. self.id2word is None)')

        with tf.device('/cpu:0'):
            with open(outfilename, 'w') as fh:
                for x in sorted(list(self.id2word.keys())):
                    embed = tf.nn.embedding_lookup(self.embedding, x).numpy()
                    word = self.id2word[x]
                    fh.write('{word} {embedding}\n'.format(word=word, embedding=' '.join(map(str, embed))))


class SkipGramWord2Vec(Word2Vec):
    """Class to run word2vec using skip grams.

    Attributes:
        word2id: A dictionary where the keys are nodes/words and values are integers that represent those nodes/words.
        id2word: A dictionary where the keys are integers and values are the nodes represented by the integers.
        data: A list or list of lists (if sentences or paths from node2vec).
        learning_rate: A float between 0 and 1 that controls how fast the model learns to solve the problem.
        batch_size: The size of each "batch" or slice of the data to sample when training the model.
        num_steps: The number of epochs to run when training the model.
        embedding_size: Dimension of embedded vectors.
        max_vocabulary_size: Maximum number of words. Total number of different words in the vocabulary.
        min_occurrence: Minimum number of times a word needs to appear to be included.
        skip_window: How many words to consider left and right.
        num_skips: How many times to reuse an input to generate a label.
        num_sampled: Number of negative examples to sample.
        display: An integer of the number of words to display.
        embedding: A 2D tensor with shape (samples, sequence_length), where each entry is a sequence of integers.
        list_of_lists: A boolean which indicates whether or not the input data contains a list of lists.
        optimizer: The TensorFlow optimizer to use.
        data_index: An integer that stores the index of data for use when creating batches.
        current_sentence: An integer which is used to track the number of sentences or random walks.
        num_sentences: An integer that stores the total number of sentences.
        nce_weights: A variable that stores the classifier weights.
        nce_biases: A variable that stores classifier biases.
    """

    def __init__(self, data: list, worddictionary: dict, reverse_worddictionary: dict, learning_rate: float = 0.1,
                 batch_size: int = 128, num_steps: int = 100,  # default=3000000
                 embedding_size: int = 200, max_vocabulary_size: int = 50000, min_occurrence: int = 1,  # default=2
                 skip_window: int = 3, num_skips: int = 2, num_sampled: int = 7,  # default=64
                 display=None):

        super().__init__(data, worddictionary, reverse_worddictionary, learning_rate, batch_size, num_steps,
                         embedding_size, max_vocabulary_size, min_occurrence, skip_window, num_skips, num_sampled,
                         display)

        # could comment these out if sticking with inheritance from super
        self.data = data
        self.word2id = worddictionary
        self.id2word = reverse_worddictionary

        # takes the input data and goes through each element
        # first, check each element is a list
        if any(isinstance(el, list) for el in self.data):
            for el in self.data:
                # then, check each element of the list is integer
                if any(isinstance(item, int) for item in el):
                    # graph version
                    self.list_of_lists = True
                else:
                    self.list_of_lists = False
                    raise TypeError('The item must be a list of walks where each walk is a sequence of (int) nodes.')

        self.calculate_vocabulary_size()

        # set vocabulary size
        # with toy exs the # of nodes might be lower than the default value of num_sampled of 64. num_sampled needs to
        # be less than the # of exs (num_sampled is the # of negative samples that get evaluated per positive ex)
        if self.num_sampled > self.vocabulary_size:
            self.num_sampled = self.vocabulary_size/2

        self.optimizer = tf.keras.optimizers.SGD(learning_rate)
        self.data_index: int = 0
        self.current_sentence: int = 0
        self.num_sentences: int = len(self.data)

        # do not display examples during training unless the user calls add_display_words (i.e. default is None)
        self.display = None

        # ensure the following ops & var are assigned on CPU (some ops are not compatible on GPU)
        with tf.device('/cpu:0'):
            # create embedding (each row is a word embedding vector) with shape (#n_words, dims) and dim = vector size
            self.embedding = tf.Variable(tf.random.normal([self.vocabulary_size, embedding_size]))

            # construct the variables for the NCE loss
            self.nce_weights = tf.Variable(tf.random.normal([self.vocabulary_size, embedding_size]))
            self.nce_biases = tf.Variable(tf.zeros([self.vocabulary_size]))

    def get_embedding(self, x: np.ndarray):
        """Get the embedding corresponding to the data points in x. Note, we ensure that this code is carried out on
        the CPU because some ops are not compatible with the GPU.

        Args:
            x: Data point index, with shape (batch_size,).

        Returns:
            embedding: Corresponding embeddings, with shape (batch_size, embedding_dimension).
        """
        with tf.device('/cpu:0'):

            # lookup the corresponding embedding vectors for each sample in x
            embedding = tf.nn.embedding_lookup(self.embedding, x)

            return embedding

    def nce_loss(self, x_embed: tf.Tensor, y: np.ndarray):
        """Calculates the noise-contrastive estimation (NCE) training loss estimation for each batch.

        Args:
            x_embed: A Tensor with shape [batch_size, dim].
            y: A Tensor containing the target classes with shape [batch_size, num_true].

        Returns:
            loss: A batch_size 1-D tensor of per-example NCE losses.
        """

        with tf.device('/cpu:0'):
            y = tf.cast(y, tf.int64)

            # print("self.nce_weights=%s (%s) " % (self.nce_weights, type(self.nce_weights)))
            # print("self.nce_biases=%s (%s) " % (self.nce_biases,type(self.nce_biases)))
            # print("y=%s (%s)" % (y,type(y)))
            # print("x_embed=%s (%s) " % (x_embed,type(x_embed)))
            # print("self.num_sampled=%s" % type(self.num_sampled))
            # print("self.vocabulary_size=%s" % type(self.vocabulary_size))
            # exit(1)

            loss = tf.reduce_mean(
                tf.nn.nce_loss(weights=self.nce_weights,
                               biases=self.nce_biases,
                               labels=y,
                               inputs=x_embed,
                               num_sampled=self.num_sampled,
                               num_classes=self.vocabulary_size))

            return loss

    def evaluate(self, x_embed: tf.Tensor):
        """Computes the cosine similarity between a provided embedding and all other embedding vectors.

        Args:
            x_embed: A Tensor containing word embeddings.

        Returns:
            cosine_sim_op: A tensor of the cosine similarities between input data embedding and all other embeddings.
        """

        with tf.device('/cpu:0'):
            x_embed_cast = tf.cast(x_embed, tf.float32)
            x_embed_norm = x_embed_cast/tf.sqrt(tf.reduce_sum(tf.square(x_embed_cast)))
            x_embed_sqrt = tf.sqrt(tf.reduce_sum(tf.square(self.embedding), 1, keepdims=True), tf.float32)
            embedding_norm = self.embedding/x_embed_sqrt

            # calculate cosine similarity
            cosine_sim_op = tf.matmul(x_embed_norm, embedding_norm, transpose_b=True)

            return cosine_sim_op

    def next_batch(self, data: list, batch_size: int, num_skips: int, skip_window: int):
        """Generates a training batch for the skip-gram model.

        Assumptions: All of the data is in one and only one list (for instance, the data might derive from a book).

        Args:
            data: A list of words or nodes.
            batch_size: An integer specifying the size of the batch to generate.
            num_skips: The number of data points to extract for each center node.
            skip_window: The size of sampling windows (technically half-window). The window of a word `w_i` will be
                `[i - window_size, i + window_size+1]`.

        Returns:
            A list where the first item is a batch and the second item is the batch's labels.
        """

        # check that batch_size is evenly divisible by num_skips and num_skips is less or equal to skip window size
        assert batch_size % num_skips == 0 and num_skips <= 2 * skip_window

        batch = np.ndarray(shape=(batch_size,), dtype=np.int32)
        labels = np.ndarray(shape=(batch_size, 1), dtype=np.int32)

        # get window size (words left and right + current one)
        span = (2 * skip_window) + 1
        buffer = collections.deque(maxlen=span)

        if self.data_index + span > len(data):
            self.data_index = 0

        buffer.extend(data[self.data_index:self.data_index + span])

        # print('data {data}'.format(data=data[self.data_index:self.data_index + span]))
        # print('buffer: {buffer}'.format(buffer=buffer))
        self.data_index += span
        for i in range(batch_size // num_skips):
            context_words = [w for w in range(span) if w != skip_window]
            words_to_use = random.sample(context_words, num_skips)

            for j, context_word in enumerate(words_to_use):
                # j is the index of an element of words_to_use and context_word is that element
                # buffer -- the sliding window
                # buffer[skip_window] - the center element of the sliding window
                # buffer[context_word] - the int value of the word/node we try to predict with the skip-gram model
                batch[i * num_skips + j] = buffer[skip_window]
                labels[i * num_skips + j, 0] = buffer[context_word]

            if self.data_index == len(data):
                # when the end of the string is reached, reset to beginning
                buffer.extend(data[0:span])
                self.data_index = span
            else:
                buffer.append(data[self.data_index])

                # move the sliding window 1 position to the right
                self.data_index += 1

        # backtrack a little bit to avoid skipping words in the end of a batch.
        self.data_index = (self.data_index + len(data) - span) % len(data)

        return batch, labels

    def next_batch_from_list_of_lists(self, walk_count: int, num_skips: int, skip_window: int):
        """Generate training batch for the skip-gram model.

        Assumption: This assumes that all of the data is stored as a list of lists (e.g., node2vec).

        Args:
            walk_count: The number of walks (sublists or sentences) to ingest.
            num_skips: The number of data points to extract for each center node.
            skip_window: The size of sampling windows (technically half-window). The window of a word `w_i` will be
                `[i - window_size, i + window_size+1]`.

        Returns:
            A list where the first item us a batch and the second item is the batch's labels.
        """

        assert num_skips <= 2 * skip_window

        # self.data is a list of lists, e.g., [[1, 2, 3], [5, 6, 7]]
        span = 2 * skip_window + 1
        batch = np.ndarray(shape=(0,), dtype=np.int32)
        labels = np.ndarray(shape=(0, 1), dtype=np.int32)

        for i in range(walk_count):
            self.current_sentence += 1

            # sentence can be one random walk
            sentence = self.data[self.current_sentence]
            batch_count = (len(sentence) - span) + 1

            # get batch data
            current_batch, current_labels = self.next_batch(sentence, batch_count, num_skips, skip_window)
            batch = np.append(batch, current_batch)
            labels = np.append(labels, current_labels, axis=0)

            if self.current_sentence == self.num_sentences:
                self.current_sentence = 0

        return batch, labels

    def run_optimization(self, x: np.array, y: np.array):
        """Runs optimization for each batch by retrieving an embedding and calculating NCE loss. Once the loss has
        been calculated, the gradients are computed and the weights and biases are updated accordingly.

        Args:
            x: An array of integers to use as batch training data.
            y: An array of labels to use when evaluating loss for an epoch.

        Returns:
            None.
        """

        with tf.device('/cpu:0'):
            # wrap computation inside a GradientTape for automatic differentiation
            with tf.GradientTape() as g:
                embedding = self.get_embedding(x)
                loss = self.nce_loss(embedding, y)

            # compute gradients
            gradients = g.gradient(loss, [self.embedding, self.nce_weights, self.nce_biases])

            # update W and b following gradients
            self.optimizer.apply_gradients(zip(gradients, [self.embedding, self.nce_weights, self.nce_biases]))

            return None

    def train(self, display_step: int = 2000):
        """Trains a SkipGram model.

        Args:
            display_step: An integer that is used to determine the number of steps to display when training the model.

        Returns:
            None.
        """

        # words for testing; display_step = 2000; eval_step = 2000
        if display_step is not None:
            for w in self.display_examples:
                print('{word}: id={index}'.format(word=self.id2word[w], index=w))

        x_test = np.array(self.display_examples)

        # run training for the given number of steps
        for epoch in range(1, self.num_steps + 1):
            if self.list_of_lists:
                walk_count = 2
                batch_x, batch_y = self.next_batch_from_list_of_lists(walk_count, self.num_skips, self.skip_window)
            else:
                batch_x, batch_y = self.next_batch(self.data, self.batch_size, self.num_skips, self.skip_window)

            self.run_optimization(batch_x, batch_y)

            if epoch % display_step == 0 or epoch == 1:
                loss = self.nce_loss(self.get_embedding(batch_x), batch_y)
                print('step: {}, loss: {}'.format(epoch, loss))

            # evaluation
            if self.display is not None and (epoch % self.eval_step == 0 or epoch == 1):
                print('Evaluation...')
                sim = self.evaluate(self.get_embedding(x_test)).numpy()
                print(sim[0])

                for i in range(len(self.display_examples)):
                    top_k = 8  # number of nearest neighbors
                    nearest = (-sim[i, :]).argsort()[1:top_k + 1]
                    disp_example = self.id2word[self.display_examples[i]]
                    log_str = '{} nearest neighbors:'.format(disp_example)

                    for k in range(top_k):
                        log_str = '{} {},'.format(log_str, self.id2word[nearest[k]])

                    print(log_str)

        return None


class ContinuousBagOfWordsWord2Vec(Word2Vec):
    """Class to run word2vec using skip grams.

    Attributes:
        word2id: A dictionary where the keys are nodes/words and values are integers that represent those nodes/words.
        id2word: A dictionary where the keys are integers and values are the nodes represented by the integers.
        data: A list or list of lists (if sentences or paths from node2vec).
        learning_rate: A float between 0 and 1 that controls how fast the model learns to solve the problem.
        batch_size: The size of each "batch" or slice of the data to sample when training the model.
        num_steps: The number of epochs to run when training the model.
        embedding_size: Dimension of embedded vectors.
        max_vocabulary_size: Maximum number of words. Total number of different words in the vocabulary.
        min_occurrence: Minimum number of times a word needs to appear to be included.
        skip_window: How many words to consider left and right.
        num_skips: How many times to reuse an input to generate a label.
        num_sampled: Number of negative examples to sample.
        display: An integer of the number of words to display.
        embedding: A 2D tensor with shape (samples, sequence_length), where each entry is a sequence of integers.
        batcher: A list of CBOW data for training; the first item is a batch and the second item is the batch labels.
        list_of_lists: A boolean which indicates whether or not the input data contains a list of lists.
        optimizer: The TensorFlow optimizer to use.
        data_index: An integer that stores the index of data for use when creating batches.
        current_sentence: An integer which is used to track the number of sentences or random walks.
        num_sentences: An integer that stores the total number of sentences.
        softmax_weights: A variable that stores the classifier weights.
        softmax_biases: A variable that stores classifier biases.

    """

    def __init__(self, data: list, worddictionary: dict, reverse_worddictionary: dict, learning_rate: float = 0.1,
                 batch_size: int = 128, num_steps: int = 1000,  # default=3000000
                 embedding_size: int = 200, max_vocabulary_size: int = 50000, min_occurrence: int = 1,  # default=2
                 skip_window: int = 3, num_skips: int = 2, num_sampled: int = 7,  # default=64
                 display: int = None):

        super(ContinuousBagOfWordsWord2Vec, self).__init__(data, worddictionary, reverse_worddictionary, learning_rate,
                                                           batch_size, num_steps, embedding_size, max_vocabulary_size,
                                                           min_occurrence, skip_window, num_skips, num_sampled, display)
        self.data = data
        self.word2id = worddictionary
        self.id2word = reverse_worddictionary
        self.batcher = CBOWBatcherListOfLists(data)

        # takes the input data and goes through each element
        if any(isinstance(el, list) for el in self.data):
            self.list_of_lists = True
        else:
            self.list_of_lists = False

        self.calculate_vocabulary_size()

        # this should not be a problem with real data, but with toy exs the # of nodes might be lower than the default
        # value of num_sampled of 64. However, num_sampled needs to be less than the # of exs (num_sampled is the #
        # of negative samples that get evaluated per positive ex)
        if self.num_sampled > self.vocabulary_size:
            self.num_sampled = self.vocabulary_size/2

        self.optimizer = tf.keras.optimizers.SGD(learning_rate)
        self.data_index = 0
        self.current_sentence = 0
        self.num_sentences = len(self.data)

        # do not display examples during training unless the user calls add_display_words, i.e., default is None
        self.display = None

        # ensure the following ops & var are assigned on CPU (some ops are not compatible on GPU)
        with tf.device('/cpu:0'):
            # create embedding (each row is a word embedding vector) with shape (#n_words, dims) and dim = vector size
            self.embedding = tf.Variable(
                tf.random.uniform([self.vocabulary_size, embedding_size], -1.0, 1.0, dtype=tf.float32))

            # should we initialize with uniform or normal?
            # # tf.Variable(tf.random.normal([self.vocabulary_size, embedding_size]))

            # construct the variables for the NCE loss
            # self.nce_weights = tf.Variable(tf.random.normal([self.vocabulary_size, embedding_size]))
            # self.nce_biases = tf.Variable(tf.zeros([self.vocabulary_size]))
            # softmax Weights and Biases
            self.softmax_weights = tf.Variable(tf.random.truncated_normal([self.vocabulary_size, embedding_size],
                                                                          stddev=0.5/math.sqrt(embedding_size),
                                                                          dtype=tf.float32))

            self.softmax_biases = tf.Variable(tf.random.uniform([self.vocabulary_size], 0.0, 0.01))

    def get_embedding(self, x):
        """        :param x: A batch-size long list of windows of words (sliding windows) e.g.,
        [[ 2619 15572 15573 15575 15576 15577], [15572 15573 15574 15576 15577 15578], ...]
        The function performs embedding lookups for each column in the input (except the middle one)
        and then averages the them to produce a word vector
        The dimension of x is (batchsize, 2*skip_window), e.g., (128,6)
        Note that x does not contain the middle word
        """

        stacked_embeddings = None
        # print('Defining {} embedding lookups representing each word in the context'.format(2 * self.skip_window))

        for i in range(2 * self.skip_window):
            embedding_i = tf.nn.embedding_lookup(self.embedding, x[:, i])
            # print("embedding_i shape", embedding_i.shape)
            x_size, y_size = embedding_i.get_shape().as_list()  # added ',_' -- is this correct?
            if stacked_embeddings is None:
                stacked_embeddings = tf.reshape(embedding_i, [x_size, y_size, 1])
            else:
                stacked_embeddings = tf.concat(axis=2, values=[stacked_embeddings,
                                                               tf.reshape(embedding_i, [x_size, y_size, 1])])

        assert stacked_embeddings.get_shape().as_list()[2] == 2 * self.skip_window
        # print("Stacked embedding size: %s" % stacked_embedings.get_shape().as_list())
        mean_embeddings = tf.reduce_mean(stacked_embeddings, 2, keepdims=False)
        # print("Reduced mean embedding size: %s" % mean_embeddings.get_shape().as_list())

        return mean_embeddings

    def get_loss(self, mean_embeddings, y):
        """Computes the softmax loss, using a sample of the negative labels each time. The inputs are embeddings of the
        train words with this loss we optimize weights, biases, embeddings.

        Args:
            mean_embeddings:
            y:

        Returns:
            loss:

        """

        y = tf.cast(y, tf.int64)
        loss = tf.reduce_mean(
            tf.nn.sampled_softmax_loss(weights=self.softmax_weights,
                                       biases=self.softmax_biases,
                                       inputs=mean_embeddings,
                                       labels=y,
                                       num_sampled=self.num_sampled,
                                       num_classes=self.vocabulary_size)
                                )

        return loss

    def nce_loss(self, x_embed, y):
        """Computes the average NCE loss for the batch.

        """

        with tf.device('/cpu:0'):
            y = tf.cast(y, tf.int64)

            # print("self.nce_weights=%s (%s) " % (self.nce_weights, type(self.nce_weights)))
            # print("self.nce_biases=%s (%s) " % (self.nce_biases,type(self.nce_biases)))
            # print("y=%s (%s)" % (y,type(y)))
            # print("x_embed=%s (%s) " % (x_embed,type(x_embed)))
            # print("self.num_sampled=%s" % type(self.num_sampled))
            # print("self.vocabulary_size=%s" % type(self.vocabulary_size))
            # exit(1)

            loss = tf.reduce_mean(
                tf.nn.nce_loss(weights=self.softmax_weights,
                               biases=self.softmax_biases,
                               labels=y,
                               inputs=x_embed,
                               num_sampled=self.num_sampled,
                               num_classes=self.vocabulary_size))

            return loss

    def evaluate(self, x_embed):
        """

        """

        with tf.device('/cpu:0'):
            # Compute the cosine similarity between input data embedding and every embedding vectors
            x_embed = tf.cast(x_embed, tf.float32)
            x_embed_norm = x_embed / tf.sqrt(tf.reduce_sum(tf.square(x_embed)))
            embedding_norm = self.embedding / tf.sqrt(tf.reduce_sum(tf.square(self.embedding), 1, keepdims=True),
                                                      tf.float32)
            cosine_sim_op = tf.matmul(x_embed_norm, embedding_norm, transpose_b=True)
            return cosine_sim_op

    def generate_batch_cbow(self, data, batch_size, window_size):
        """Generates the next batch of data for CBOW.

        Args:
            data: list of words. TODO make class variable
            batch_size: number of examples to process at once.
            window_size: number of words to consider on each side of central word.

        Returns:
            A batch of CBOW data for training.

        """

        # span is the total size of the sliding window we look at [skip_window central_word skip_window]
        span = 2 * window_size + 1

        # two numpy arrays to hold target (batch) and context words (labels). Batch has span-1=2*window_size columns
        batch = np.ndarray(shape=(batch_size, span - 1), dtype=np.int32)
        labels = np.ndarray(shape=(batch_size, 1), dtype=np.int64)

        # The buffer holds the data contained within the span and the deque essentially implements a sliding window
        buffer = collections.deque(maxlen=span)

        # fill the buffer and update the data_index
        for _ in range(span):
            buffer.append(data[self.data_index])
            self.data_index = (self.data_index + 1) % len(data)

        # for each batch index, we iterate through span elements to fill in the columns of batch array
        for i in range(batch_size):
            target = window_size  # target word at the center of the buffer
            col_idx = 0

            for j in range(span):
                if j == span // 2:
                    continue  # i.e., ignore the center wortd
                batch[i, col_idx] = buffer[j]
                col_idx += 1
            labels[i, 0] = buffer[target]

            # move the span by 1, i.e., sliding window, since buffer is deque with limited size
            buffer.append(data[self.data_index])
            self.data_index = (self.data_index + 1) % len(data)

        return batch, labels

    def next_batch_from_list_of_lists(self, walk_count, num_skips, skip_window):
        """Generates training batch for the skip-gram model. This assumes that all of the data is in one and only one
        list (for instance, the data might derive from a book). To get batches from a list of lists (e.g., node2vec),
        use the 'next_batch_from_list_of_list' function.

        Args:
            walk_count: number of walks (sublists or sentences) to ingest.
            num_skips: The number of data points to extract for each center node.
            skip_window: The size of the surrounding window (For instance, if skip_window=2 and num_skips=1, we look at
                5 nodes at a time, and choose one data point from the 4 nodes that surround the center node

        Returns:
            A batch of data points ready for learning.

        """

        # assert batch_size % num_skips == 0
        assert num_skips <= 2 * skip_window
        # self.data is a list of lists, e.g., [[1, 2, 3], [5, 6, 7]]
        span = 2 * skip_window + 1
        batch = np.ndarray(shape=(0,), dtype=np.int32)
        labels = np.ndarray(shape=(0, 1), dtype=np.int64)
        for _ in range(walk_count):
            sentence = self.data[self.current_sentence]
            self.current_sentence += 1
            sentence_len = len(sentence)
            batch_count = sentence_len - span + 1
            if self.list_of_lists:
                current_batch, current_labels = self.batcher.generate_batch()
                # self.next_batch_from_list_of_lists(sentence, batch_count, num_skips)
            else:
                current_batch, current_labels = self.generate_batch_cbow(sentence, batch_count, num_skips)
            batch = np.append(batch, current_batch)
            labels = np.append(labels, current_labels, axis=0)
            if self.current_sentence == self.num_sentences:
                self.current_sentence = 0

        return batch, labels

    def run_optimization(self, x, y):
        """

        """

        with tf.device('/cpu:0'):
            # Wrap computation inside a GradientTape for automatic differentiation.
            with tf.GradientTape() as g:
                emb = self.get_embedding(x)
                loss = self.nce_loss(emb, y)

            # Compute gradients.
            gradients = g.gradient(loss, [self.embedding, self.softmax_weights, self.softmax_biases])

            # Update W and b following gradients.
            self.optimizer.apply_gradients(zip(gradients, [self.embedding, self.softmax_weights, self.softmax_biases]))

    def train(self, display_step=2000):
        """

        Args:
            display_step:

        Returns:
            None.

        """

        # words for testing; display_step = 2000; eval_step = 2000
        if display_step is not None:
            for w in self.display_examples:
                print("{}: id={}".format(self.id2word[w], w))

        x_test = np.array(self.display_examples)

        # run training for the given number of steps.
        for step in range(1, self.num_steps + 1):
            batch_x, batch_y = self.generate_batch_cbow(self.data, self.batch_size, self.skip_window)
            self.run_optimization(batch_x, batch_y)

            if step % display_step == 0 or step == 1:
                loss = self.get_loss(self.get_embedding(batch_x), batch_y)
                print("step: %i, loss: %f" % (step, loss))

            # evaluation
            if self.display is not None and (step % self.eval_step == 0 or step == 1):
                print('Evaluation...\n')
                sim = self.evaluate(self.get_embedding(x_test)).numpy()
                print(sim[0])

                for i in range(len(self.display_examples)):
                    top_k = 8  # number of nearest neighbors.
                    nearest = (-sim[i, :]).argsort()[1:top_k + 1]
                    disp_example = self.id2word[self.display_examples[i]]
                    log_str = '{} nearest neighbors:'.format(disp_example)

                    for k in range(top_k):
                        log_str = '{} {},'.format(log_str, self.id2word[nearest[k]])

                    print(log_str)
