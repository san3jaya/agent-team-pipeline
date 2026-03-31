"""Session save/load tools — pipeline checkpoint persistence.

.. note:: Stub implementation for Phase 3.
"""

from __future__ import annotations


def save(session_id: str, state: dict) -> dict:
    """Save pipeline checkpoint state.

    Returns:
        ``{"saved": True}``
    """
    raise NotImplementedError("session.save is planned for Phase 3")


def load(session_id: str | None = None) -> dict:
    """Load the latest or a specific checkpoint.

    Returns:
        ``{"state": dict}`` or ``{"found": False}``
    """
    raise NotImplementedError("session.load is planned for Phase 3")
