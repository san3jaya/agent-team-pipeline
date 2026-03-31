"""Pure-numpy cosine similarity utilities for vector search."""

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors.

    Returns a value in ``[-1, 1]``.  Returns ``0.0`` when either vector has
    zero magnitude.

    Raises:
        ValueError: If the arrays are not 1-D or have mismatched shapes.
    """
    if a.ndim != 1 or b.ndim != 1:
        raise ValueError(
            f"Both inputs must be 1-D arrays, got shapes {a.shape} and {b.shape}"
        )
    if a.shape != b.shape:
        raise ValueError(f"Shape mismatch: {a.shape} vs {b.shape}")

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def search_similar(
    query_embedding: np.ndarray,
    stored_embeddings: list[tuple[int, np.ndarray]],
    top_k: int = 3,
    min_score: float = 0.3,
) -> list[tuple[int, float]]:
    """Find the *top_k* most similar embeddings above *min_score*.

    Args:
        query_embedding: 1-D query vector.
        stored_embeddings: Sequence of ``(id, embedding)`` pairs to search.
        top_k: Maximum number of results to return.
        min_score: Minimum cosine similarity to include in results.

    Returns:
        List of ``(id, score)`` tuples sorted by descending similarity.
    """
    if top_k < 1:
        return []

    scores: list[tuple[int, float]] = []
    for id_, emb in stored_embeddings:
        score = cosine_similarity(query_embedding, emb)
        if score >= min_score:
            scores.append((id_, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]
