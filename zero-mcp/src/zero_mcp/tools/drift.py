"""Embedding-based drift detection between a task description and code changes."""

from __future__ import annotations

from ..memory.embeddings import EmbeddingModel
from ..memory.similarity import cosine_similarity

# File-name patterns that are suspicious when they appear unexpectedly.
_SUSPICIOUS_PATTERNS = [
    "migration",
    "schema",
    "config",
    ".env",
    "package.json",
    "composer.json",
    "cargo.toml",
    "go.mod",
    "pyproject.toml",
]


def check(
    model: EmbeddingModel,
    task_description: str,
    changed_files: list[str],
    diff_summary: str,
) -> dict:
    """Check whether code changes drift from the stated task.

    The drift score is ``1 − cosine_similarity(task_emb, diff_emb)`` so that
    **0 = perfectly aligned** and **1 = completely unrelated**.

    Verdicts:
    - ``<0.3`` → ``"aligned"``
    - ``0.3–0.6`` → ``"minor_drift"``
    - ``>0.6`` → ``"significant_drift"``

    Returns:
        ``{"score": float, "similarity": float, "flags": [...], "verdict": str}``
    """
    task_emb = model.embed(task_description)
    diff_emb = model.embed(diff_summary)

    similarity = cosine_similarity(task_emb, diff_emb)
    drift_score = max(0.0, min(1.0, 1.0 - similarity))

    flags: list[str] = []

    for f in changed_files:
        f_lower = f.lower()
        for pattern in _SUSPICIOUS_PATTERNS:
            if pattern in f_lower:
                file_emb = model.embed(f)
                file_sim = cosine_similarity(task_emb, file_emb)
                if file_sim < 0.3:
                    flags.append(f"Unexpected file change: {f}")
                break  # one flag per file is enough

    if drift_score < 0.3:
        verdict = "aligned"
    elif drift_score < 0.6:
        verdict = "minor_drift"
    else:
        verdict = "significant_drift"

    return {
        "score": round(drift_score, 3),
        "similarity": round(similarity, 3),
        "flags": flags,
        "verdict": verdict,
    }
