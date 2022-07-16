"""TransE model."""
from ensmallen import Graph
import pandas as pd
from tensorflow.keras import Model
from embiggen.embedders.tensorflow_embedders.siamese import Siamese
from embiggen.utils.abstract_models import EmbeddingResult


class TransETensorFlow(Siamese):
    """TransE model."""

    def _build_output(
        self,
        *args
    ):
        """Returns the five input tensors, unchanged."""
        return args[:-2]

    @classmethod
    def model_name(cls) -> str:
        """Returns name of the current model."""
        return "TransE"

    @classmethod
    def requires_edge_types(cls) -> bool:
        return True

    def _extract_embeddings(
        self,
        graph: Graph,
        model: Model,
        return_dataframe: bool
    ) -> EmbeddingResult:
        """Returns embedding from the model.

        Parameters
        ------------------
        graph: Graph
            The graph that was embedded.
        model: Model
            The Keras model used to embed the graph.
        return_dataframe: bool
            Whether to return a dataframe of a numpy array.
        """
        node_embedding = self.get_layer_weights(
            "NodeEmbedding",
            model,
            drop_first_row=False
        )
        edge_type_embedding = self.get_layer_weights(
            "BiasEdgeTypeEmbedding",
            model,
            drop_first_row=graph.has_unknown_edge_types()
        )

        if return_dataframe:
            node_embedding = pd.DataFrame(
                node_embedding,
                index=graph.get_node_names()
            )
            edge_type_embedding = pd.DataFrame(
                edge_type_embedding,
                index=graph.get_unique_edge_type_names()
            )

        return EmbeddingResult(
            embedding_method_name=self.model_name(),
            node_embeddings=node_embedding,
            edge_type_embeddings=edge_type_embedding
        )

    @classmethod
    def can_use_node_types(cls) -> bool:
        """Returns whether the model can optionally use node types."""
        return False