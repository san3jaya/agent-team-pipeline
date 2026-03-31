"""OpenCode session file parser.

.. note:: Stub implementation for Phase 4.
"""

from __future__ import annotations

from pathlib import Path


def parse_session(db_path: Path) -> dict:
    """Parse an OpenCode session SQLite database for token usage.

    Args:
        db_path: Path to the OpenCode session ``.db`` file.

    Returns:
        ``{"found": True, "accuracy": "exact", "steps": [...]}``
        or ``{"found": False, "reason": str}``.
    """
    raise NotImplementedError("opencode.parse_session is planned for Phase 4")
