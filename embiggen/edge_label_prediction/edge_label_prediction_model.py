"""Module providing abstract edge label prediction model."""
from typing import Optional, Union, List, Dict, Any, Tuple
import pandas as pd
import numpy as np
from ensmallen import Graph
from ..utils import AbstractClassifierModel, format_list


class AbstractEdgeLabelPredictionModel(AbstractClassifierModel):
    """Class defining an abstract edge label prediction model."""

    def __init__(self):
        self._is_binary_prediction_task = None
        self._is_multilabel_prediction_task = None
        super().__init__()
    
    def requires_edge_types() -> bool:
        """Returns whether this method requires node types."""
        return True

    @staticmethod
    def task_name() -> str:
        """Returns name of the task this model is used for."""
        return "Edge Label Prediction"

    @staticmethod
    def is_topological() -> bool:
        return False

    def is_binary_prediction_task(self) -> bool:
        """Returns whether the model was fit on a binary prediction task."""
        return self._is_binary_prediction_task

    def is_multilabel_prediction_task(self) -> bool:
        """Returns whether the model was fit on a multilabel prediction task."""
        return self._is_multilabel_prediction_task

    def get_available_evaluation_schemas(self) -> List[str]:
        """Returns available evaluation schemas for this task."""
        return [
            "Stratified Monte Carlo",
            "Monte Carlo",
            "Stratified Kfold"
            "Kfold"
        ]

    def split_graph_following_evaluation_schema(
        self,
        graph: Graph,
        evaluation_schema: str,
        number_of_holdouts: int,
        random_state: int,
        holdouts_kwargs: Dict[str, Any],
        holdout_number: int
    ) -> Tuple[Graph]:
        """Return train and test graphs tuple following the provided evaluation schema.

        Parameters
        ----------------------
        graph: Graph
            The graph to split.
        evaluation_schema: str
            The evaluation schema to follow.
        number_of_holdouts: int
            The number of holdouts that will be generated throught the evaluation.
        random_state: int
            The random state for the evaluation
        holdouts_kwargs: Dict[str, Any]
            The kwargs to be forwarded to the holdout method.
        holdout_number: int
            The current holdout number.
        """
        if evaluation_schema in ("Stratified Monte Carlo", "Monte Carlo"):
            return graph.get_edge_label_holdout_graphs(
                **holdouts_kwargs,
                use_stratification="Stratified" in evaluation_schema,
                random_state=random_state+holdout_number,
            )
        if evaluation_schema in ("Kfold", "Stratified Kfold"):
            return graph.get_edge_label_kfold(
                k=number_of_holdouts,
                k_index=holdout_number,
                use_stratification="Stratified" in evaluation_schema,
                random_state=random_state,
            )
        raise ValueError(
            f"The requested evaluation schema `{evaluation_schema}` "
            "is not available. The available evaluation schemas "
            f"are: {format_list(self.get_available_evaluation_schemas())}."
        )

    def _evaluate(
        self,
        graph: Graph,
        train: Graph,
        test: Graph,
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[str, pd.DataFrame, np.ndarray]]]] = None,
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[str, pd.DataFrame, np.ndarray]]]] = None,
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[str, pd.DataFrame, np.ndarray]]]] = None,
        subgraph_of_interest: Optional[Graph] = None,
        random_state: int = 42,
    ) -> List[Dict[str, Any]]:
        """Return model evaluation on the provided graphs."""
        train_size = train.get_known_edge_types_number() / graph.get_known_edge_types_number()
        performance = []
        for evaluation_mode, evaluation_graph in (
            ("train", train),
            ("test", test),
        ):
            prediction_probabilities = self.predict_proba(
                evaluation_graph,
                node_features=node_features,
                node_type_features=node_type_features,
                edge_features=edge_features
            )

            if self.is_binary_prediction_task():
                prediction_probabilities = prediction_probabilities[:, 1]
                predictions = prediction_probabilities > 0.5
            else:
                predictions = prediction_probabilities.argmax(axis=-1)

            labels = graph.get_known_edge_type_ids()

            if graph.has_unknown_node_types():
                mask = graph.get_known_node_types_mask()
                prediction_probabilities = prediction_probabilities[mask]
                predictions = predictions[mask]

            performance.append({
                "evaluation_mode": evaluation_mode,
                "train_size": train_size,
                "known_edges_number": graph.get_known_node_types_number(),
                **self.evaluate_predictions(
                    predictions,
                    labels
                ),
                **self.evaluate_prediction_probabilities(
                    prediction_probabilities,
                    labels
                ),
            })

        return performance

    def fit(
        self,
        graph: Graph,
        support: Optional[Graph] = None,
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
    ):
        """Execute predictions on the provided graph.

        Parameters
        --------------------
        graph: Graph
            The graph to run predictions on.
        support: Optional[Graph] = None
            The graph describiding the topological structure that
            includes also the above graph. This parameter
            is mostly useful for topological classifiers
            such as Graph Convolutional Networks.
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node features to use.
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node type features to use.
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The edge features to use.
        """
        if node_type_features is not None:
            raise NotImplementedError(
                "Support for node type features is not currently available for any "
                "of the edge-label prediction models."
            )

        self._is_binary_prediction_task = graph.get_edge_types_number() == 2
        self._is_multilabel_prediction_task = graph.is_multigraph()

        super().fit(
            graph=graph,
            support=support,
            node_features=node_features,
            node_type_features=node_type_features,
            edge_features=edge_features,
        )

    @staticmethod
    def can_use_edge_types() -> bool:
        """Returns whether the model can optionally use edge types."""
        return True

    def is_using_edge_types(self) -> bool:
        """Returns whether the model is parametrized to use edge types."""
        return True