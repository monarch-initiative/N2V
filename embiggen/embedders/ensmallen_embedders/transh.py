"""Module providing TransH implementation."""
from ensmallen import Graph
import pandas as pd
from embiggen.embedders.ensmallen_embedders.siamese_model import SiameseEnsmallen
from embiggen.utils import EmbeddingResult


class TransHEnsmallen(SiameseEnsmallen):
    """Class implementing the TransH algorithm."""

    def __init__(
        self,
        embedding_size: int = 100,
        relu_bias: float = 1.0,
        epochs: int = 100,
        learning_rate: float = 0.01,
        learning_rate_decay: float = 0.9,
        random_state: int = 42,
        verbose: bool = True,
        enable_cache: bool = False
    ):
        """Create new abstract Node2Vec method.

        Parameters
        --------------------------
        model_name: str
            The model to instantiate.
        embedding_size: int = 100
            Dimension of the embedding.
        relu_bias: float = 1.0
            Bias to use for the relu.
            In the TransH paper it is called gamma.
        epochs: int = 100
            The number of epochs to run the model for, by default 10.
        learning_rate: float = 0.01
            The learning rate to update the gradient, by default 0.01.
        learning_rate_decay: float = 0.9
            Factor to reduce the learning rate for at each epoch. By default 0.9.
        random_state: int = 42
            Random state to reproduce the embeddings.
        verbose: bool = True
            Whether to show loading bars.
        enable_cache: bool = False
            Whether to enable the cache, that is to
            store the computed embedding.
        """
        super().__init__(
            embedding_size=embedding_size,
            relu_bias=relu_bias,
            epochs=epochs,
            learning_rate=learning_rate,
            learning_rate_decay=learning_rate_decay,
            random_state=random_state,
            verbose=verbose,
            enable_cache=enable_cache,
        )

    def _fit_transform(
        self,
        graph: Graph,
        return_dataframe: bool = True,
    ) -> EmbeddingResult:
        """Return node embedding."""
        node_embedding, mult_edge_type_embedding, bias_edge_type_embedding = self._model.fit_transform(
            graph,
        )
        if return_dataframe:
            node_embedding = pd.DataFrame(
                node_embedding,
                index=graph.get_node_names()
            )
            mult_edge_type_embedding = pd.DataFrame(
                mult_edge_type_embedding,
                index=graph.get_unique_edge_type_names()
            )
            bias_edge_type_embedding = pd.DataFrame(
                bias_edge_type_embedding,
                index=graph.get_unique_edge_type_names()
            )

        return EmbeddingResult(
            embedding_method_name=self.model_name(),
            node_embeddings=node_embedding,
            edge_type_embeddings=[
                mult_edge_type_embedding,
                bias_edge_type_embedding
            ]
        )

    @classmethod
    def model_name(cls) -> str:
        """Returns name of the model."""
        return "TransH"

    @classmethod
    def requires_edge_types(cls) -> bool:
        return True