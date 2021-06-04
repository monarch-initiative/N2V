"""Siamese network for node-embedding including optionally node types and edge types."""
from typing import Optional, Union

import numpy as np
import pandas as pd
import tensorflow as tf
from ensmallen_graph import EnsmallenGraph
from tensorflow.keras import backend as K  # pylint: disable=import-error
from tensorflow.keras.optimizers import \
    Optimizer  # pylint: disable=import-error

from .siamese import Siamese


class TransE(Siamese):
    """Siamese network for node-embedding including optionally node types and edge types."""

    def __init__(
        self,
        graph: EnsmallenGraph,
        embedding_size: int = 100,
        distance_metric: str = "L2",
        embedding: Union[np.ndarray, pd.DataFrame] = None,
        extra_features: Union[np.ndarray, pd.DataFrame] = None,
        model_name: str = "TransE",
        optimizer: Union[str, Optimizer] = None
    ):
        """Create new sequence Embedder model.

        Parameters
        -------------------------------------------
        vocabulary_size: int = None,
            Number of terms to embed.
            In a graph this is the number of nodes, while in a text is the
            number of the unique words.
            If None, the seed embedding must be provided.
            It is not possible to provide both at once.
        embedding_size: int = 100,
            Dimension of the embedding.
            If None, the seed embedding must be provided.
            It is not possible to provide both at once.
        distance_metric: str = "L2",
            The distance to use for the loss function.
            Supported methods are L1, L2 and COSINE.
        embedding: Union[np.ndarray, pd.DataFrame] = None,
            The seed embedding to be used.
            Note that it is not possible to provide at once both
            the embedding and either the vocabulary size or the embedding size.
        extra_features: Union[np.ndarray, pd.DataFrame] = None,
            Optional extra features to be used during the computation
            of the embedding. The features must be available for all the
            elements considered for the embedding.
        model_name: str = "Word2Vec",
            Name of the model.
        optimizer: Union[str, Optimizer] = "nadam",
            The optimizer to be used during the training of the model.
        window_size: int = 4,
            Window size for the local context.
            On the borders the window size is trimmed.
        negative_samples: int = 10,
            The number of negative classes to randomly sample per batch.
            This single sample of negative classes is evaluated for each element in the batch.
        """
        self._distance_metric = distance_metric
        super().__init__(
            graph=graph,
            use_node_types=False,
            use_edge_types=True,
            node_embedding_size=embedding_size,
            edge_type_embedding_size=embedding_size,
            embedding=embedding,
            extra_features=extra_features,
            model_name=model_name,
            optimizer=optimizer,
        )

    def _build_output(
        self,
        src_node_embedding: tf.Tensor,
        dst_node_embedding: tf.Tensor,
        edge_type_embedding: Optional[tf.Tensor] = None,
        edge_types_input: Optional[tf.Tensor] = None,
    ):
        """Return output of the model."""
        if self._distance_metric == "L1":
            return K.sum(src_node_embedding + edge_type_embedding - dst_node_embedding)
        if self._distance_metric == "L2":
            return K.sum(K.square(src_node_embedding + edge_type_embedding - dst_node_embedding))
        if self._distance_metric == "COSINE":
            return 1.0 - tf.losses.cosine_similarity(src_node_embedding + edge_type_embedding, dst_node_embedding)
        raise ValueError(
            "Given distance metric {} is not supported.".format(self._distance_metric))
