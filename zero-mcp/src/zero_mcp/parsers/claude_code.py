"""Claude Code session file parser.

.. note:: Stub implementation for Phase 4.
"""

from __future__ import annotations

from pathlib import Path


def parse_session(session_path: Path) -> dict:
    """Parse a Claude Code session directory for token usage.

    Args:
        session_path: Path to the Claude Code session directory.

    Returns:
        ``{"found": True, "accuracy": "exact", "steps": [...]}``
        or ``{"found": False, "reason": str}``.
    """
    raise NotImplementedError("claude_code.parse_session is planned for Phase 4")
