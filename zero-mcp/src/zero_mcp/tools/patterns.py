"""Thin wrappers around :class:`~zero_mcp.memory.store.VectorStore` pattern ops.

Each function accepts an already-initialised *store* and returns a plain dict
matching the output shapes defined in DESIGN-SPEC §5.4.
"""

from __future__ import annotations

from ..memory.store import VectorStore
from ..config.settings import DEFAULT_MIN_SCORE, DEFAULT_TOP_K


def search(
    store: VectorStore,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    project: str | None = None,
    min_score: float = DEFAULT_MIN_SCORE,
) -> dict:
    """Search stored patterns by semantic similarity.

    Returns:
        ``{"results": [{"name", "context", "approach", "outcome", "score"}, …]}``
    """
    results = store.search_patterns(query, top_k=top_k, project=project, min_score=min_score)
    return {"results": results}


def store(
    store: VectorStore,
    name: str,
    context: str,
    approach: str,
    outcome: str,
    project: str | None = None,
) -> dict:
    """Store a new pattern.

    Returns:
        ``{"id": <int>, "stored": True}``
    """
    id_ = store.store_pattern(name, context, approach, outcome, project)
    return {"id": id_, "stored": True}


def prune(
    store: VectorStore,
    max_age_days: int = 90,
) -> dict:
    """Prune old / unused patterns.

    Returns:
        ``{"pruned": <int>, "remaining": <int>}``
    """
    pruned = store.prune(max_age_days=max_age_days)
    remaining = store.get_pattern_count()
    return {"pruned": pruned, "remaining": remaining}
