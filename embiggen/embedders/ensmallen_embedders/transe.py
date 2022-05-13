"""Module providing abstract Node2Vec implementation."""
from typing import  Dict, Any, Union
from ensmallen import Graph
import numpy as np
import pandas as pd
from ensmallen import models
from ...utils import AbstractEmbeddingModel


class TransEEnsmallen(AbstractEmbeddingModel):
    """Class implementing the TransE algorithm."""

    def __init__(
        self,
        embedding_size: int = 100,
        renormalize: bool = True,
        random_state: int = 42
    ):
        """Create new abstract Node2Vec method.

        Parameters
        --------------------------
        embedding_size: int = 100
            Dimension of the embedding.
        renormalize: bool = True
            Whether to renormalize at each loop, by default true.
        dtype: int = "u8"
            Dtype to use for the embedding. Note that an improper dtype may cause overflows.
        """
        self._renormalize = renormalize
        self._random_state = random_state
        self._model = models.TransE(
            embedding_size=embedding_size,
            renormalize=renormalize,
            random_state=random_state
        )

        super().__init__(
            embedding_size=embedding_size,
        )

    def parameters(self) -> Dict[str, Any]:
        """Returns parameters of the model."""
        return {
            **super().parameters(),
            **dict(
                renormalize = self._renormalize,
                random_state = self._random_state,
            )
        }

    def _fit_transform(
        self,
        graph: Graph,
        return_dataframe: bool = True,
        verbose: bool = True
    ) -> Union[Dict[str, np.ndarray], Dict[str, pd.DataFrame]]:
        """Return node embedding."""
        node_embedding, edge_type_embedding = self._model.fit_transform(
            graph,
            verbose=verbose,
        )
        if return_dataframe:
            return {
                "node_embedding": pd.DataFrame(
                    node_embedding,
                    index=graph.get_node_names()
                ),
                "edge_type_embedding": pd.DataFrame(
                    edge_type_embedding,
                    index=graph.get_unique_edge_type_names()
                ),
            }
        return {
            "node_embedding": node_embedding,
            "edge_type_embedding": edge_type_embedding,
        }

    @staticmethod
    def task_name() -> str:
        return "Node Embedding"

    @staticmethod
    def model_name() -> str:
        """Returns name of the model."""
        return "TransE"

    @staticmethod
    def library_name() -> str:
        return "Ensmallen"

    @staticmethod
    def requires_nodes_sorted_by_decreasing_node_degree() -> bool:
        return False

    @staticmethod
    def is_topological() -> bool:
        return True

    @staticmethod
    def requires_edge_weights() -> bool:
        return False

    @staticmethod
    def requires_positive_edge_weights() -> bool:
        return False

    @staticmethod
    def requires_edge_types() -> bool:
        return True

    @staticmethod
    def requires_node_types() -> bool:
        return False