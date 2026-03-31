"""Tests for ``memory.similarity``."""

import numpy as np
import pytest

from zero_mcp.memory.similarity import cosine_similarity, search_similar


class TestCosineSimilarity:
    def test_identical_vectors_return_one(self) -> None:
        v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors_return_zero(self) -> None:
        a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors_return_negative_one(self) -> None:
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([-1.0, 0.0], dtype=np.float32)
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self) -> None:
        a = np.zeros(3, dtype=np.float32)
        b = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        assert cosine_similarity(a, b) == 0.0

    def test_mismatched_shapes_raise(self) -> None:
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        with pytest.raises(ValueError):
            cosine_similarity(a, b)

    def test_2d_arrays_raise(self) -> None:
        a = np.array([[1.0, 0.0]], dtype=np.float32)
        b = np.array([[0.0, 1.0]], dtype=np.float32)
        with pytest.raises(ValueError):
            cosine_similarity(a, b)


class TestSearchSimilar:
    def test_returns_sorted_by_score(self) -> None:
        query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        stored = [
            (1, np.array([0.5, 0.5, 0.0], dtype=np.float32)),  # moderate
            (2, np.array([1.0, 0.0, 0.0], dtype=np.float32)),  # perfect
            (3, np.array([0.0, 1.0, 0.0], dtype=np.float32)),  # orthogonal
        ]
        results = search_similar(query, stored, top_k=3, min_score=0.0)
        assert results[0][0] == 2  # best match first
        assert results[0][1] == pytest.approx(1.0)

    def test_min_score_filters_low_matches(self) -> None:
        query = np.array([1.0, 0.0], dtype=np.float32)
        stored = [
            (1, np.array([1.0, 0.0], dtype=np.float32)),
            (2, np.array([0.0, 1.0], dtype=np.float32)),
        ]
        results = search_similar(query, stored, top_k=10, min_score=0.5)
        assert len(results) == 1
        assert results[0][0] == 1

    def test_top_k_limits_results(self) -> None:
        query = np.ones(3, dtype=np.float32)
        stored = [(i, np.ones(3, dtype=np.float32)) for i in range(10)]
        results = search_similar(query, stored, top_k=2, min_score=0.0)
        assert len(results) == 2

    def test_empty_stored_returns_empty(self) -> None:
        query = np.ones(3, dtype=np.float32)
        assert search_similar(query, [], top_k=5, min_score=0.0) == []
