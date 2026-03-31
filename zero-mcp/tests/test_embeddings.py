"""Tests for ``memory.embeddings`` via the MockEmbeddingModel."""

import numpy as np

from zero_mcp.config.settings import EMBEDDING_DIM


class TestMockEmbeddingModel:
    """Tests run against the mock model (no ONNX download)."""

    def test_embed_returns_correct_shape(self, mock_embedding_model) -> None:
        vec = mock_embedding_model.embed("hello world")
        assert vec.shape == (EMBEDDING_DIM,)

    def test_embed_is_normalised(self, mock_embedding_model) -> None:
        vec = mock_embedding_model.embed("test normalisation")
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 1e-5

    def test_embed_is_deterministic(self, mock_embedding_model) -> None:
        a = mock_embedding_model.embed("same text")
        b = mock_embedding_model.embed("same text")
        np.testing.assert_array_equal(a, b)

    def test_different_texts_produce_different_embeddings(
        self, mock_embedding_model
    ) -> None:
        a = mock_embedding_model.embed("foo")
        b = mock_embedding_model.embed("bar")
        assert not np.allclose(a, b)

    def test_embed_batch(self, mock_embedding_model) -> None:
        texts = ["alpha", "beta", "gamma"]
        results = mock_embedding_model.embed_batch(texts)
        assert len(results) == 3
        for vec in results:
            assert vec.shape == (EMBEDDING_DIM,)

    def test_is_loaded_property(self, mock_embedding_model) -> None:
        assert mock_embedding_model.is_loaded is True
