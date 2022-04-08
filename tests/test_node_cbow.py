"""Test to validate that the model CBOW works properly with graph walks."""
import os
import numpy as np
from embiggen import CBOW
from .test_node2vec_sequence import TestNode2VecSequence


class TestNodeCBOW(TestNode2VecSequence):
    """Unit test to validate that the model CBOW works properly with graph walks."""

    def setUp(self):
        """Setting up objects to test CBOW model on graph walks."""
        super().setUp()
        self._embedding_size = 50
        self._model = CBOW(
            vocabulary_size=self._graph.get_nodes_number(),
            embedding_size=self._embedding_size
        )
        self.assertEqual("CBOW", self._model.name)
        self._model.summary()

    def test_fit(self):
        """Test that model fitting behaves correctly and produced embedding has correct shape."""
        self._model.fit(
            self._sequence.into_dataset(),
            steps_per_epoch=self._sequence.steps_per_epoch,
            epochs=2
        )

        self.assertEqual(
            self._model.embedding.shape,
            (self._graph.get_nodes_number(), self._embedding_size)
        )

        self.assertFalse(np.isnan(self._model.embedding).any())

        self._model.save_weights(self._weights_path)
        self._model.load_weights(self._weights_path)
        self._model.save_embedding(
            self._embedding_path, self._graph.get_node_names())
        os.remove(self._weights_path)
