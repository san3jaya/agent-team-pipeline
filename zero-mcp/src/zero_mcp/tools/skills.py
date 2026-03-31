"""Project skill discovery across AI tool–native skill locations."""

from __future__ import annotations

import logging
from pathlib import Path

from ..config.settings import PROJECT_MARKERS, SKILL_DIRECTORIES
from ..memory.embeddings import EmbeddingModel

logger = logging.getLogger(__name__)

# Maximum bytes to read from a single skill file for snippet extraction.
_MAX_SKILL_BYTES = 4096


def discover(
    project_path: str,
    query: str | None = None,
    embedding_model: EmbeddingModel | None = None,
) -> dict:
    """Scan *project_path* for project markers and AI tool skill directories.

    Args:
        project_path: Absolute path to the project root.
        query: Optional semantic query — when provided (and an
            *embedding_model* is available), skill file contents are ranked
            by relevance and the top snippets are returned.
        embedding_model: Optional :class:`EmbeddingModel` used for semantic
            ranking when *query* is given.

    Returns:
        ``{"detected": [...], "snippets": [...] | None}``
    """
    root = Path(project_path).resolve()
    if not root.is_dir():
        return {"detected": [], "error": f"Not a directory: {project_path}"}

    detected: list[dict] = []

    # 1. Detect project type from marker files
    for marker_file, ecosystem in PROJECT_MARKERS.items():
        marker_path = root / marker_file
        if marker_path.exists():
            detected.append(
                {
                    "name": ecosystem,
                    "source": "project_marker",
                    "path": str(marker_path.relative_to(root)),
                    "confidence": 1.0,
                }
            )

    # 2. Scan AI tool skill directories
    skill_files: list[dict] = []
    for skill_dir_info in SKILL_DIRECTORIES:
        skill_rel = skill_dir_info["path"]
        tool_name = skill_dir_info["tool"]
        skill_path = root / skill_rel

        if skill_path.is_file():
            # Single-file skill (e.g. .windsurfrules, copilot-instructions.md)
            detected.append(
                {
                    "name": f"{tool_name}_skills",
                    "source_tool": tool_name,
                    "path": skill_rel,
                    "confidence": 1.0,
                }
            )
            skill_files.append(
                {"path": skill_path, "tool": tool_name, "rel": skill_rel}
            )
        elif skill_path.is_dir():
            # Directory of skills — enumerate contents
            detected.append(
                {
                    "name": f"{tool_name}_skills",
                    "source_tool": tool_name,
                    "path": skill_rel,
                    "confidence": 1.0,
                }
            )
            for child in sorted(skill_path.rglob("*")):
                if child.is_file() and child.suffix in {".md", ".txt", ".yaml", ".yml"}:
                    skill_files.append(
                        {
                            "path": child,
                            "tool": tool_name,
                            "rel": str(child.relative_to(root)),
                        }
                    )

    # 3. If a query is provided, rank skill snippets by similarity
    snippets: list[dict] | None = None
    if query and skill_files and embedding_model is not None:
        snippets = _rank_skills(query, skill_files, embedding_model, root)

    return {"detected": detected, "snippets": snippets}


def _rank_skills(
    query: str,
    skill_files: list[dict],
    model: EmbeddingModel,
    root: Path,
) -> list[dict]:
    """Read skill files, embed their content, and return the top matches."""
    from ..memory.similarity import cosine_similarity

    query_emb = model.embed(query)
    scored: list[tuple[float, dict]] = []

    for sf in skill_files:
        try:
            content = sf["path"].read_text(errors="replace")[:_MAX_SKILL_BYTES]
        except OSError:
            continue
        if not content.strip():
            continue

        emb = model.embed(content)
        score = cosine_similarity(query_emb, emb)
        scored.append(
            (
                score,
                {
                    "path": sf["rel"],
                    "tool": sf["tool"],
                    "content": content[:1024],  # truncate for output
                    "relevance": round(score, 3),
                },
            )
        )

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:5]]
