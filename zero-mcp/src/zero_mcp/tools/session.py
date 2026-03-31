"""Metrics tools — session tracking, step recording, reports, trends.

.. note:: Stub implementation for Phase 3.
"""

from __future__ import annotations


def start_session(
    task: str,
    classification: str,
    ai_tool: str | None = None,
    project: str | None = None,
) -> dict:
    """Start tracking a pipeline session.

    Returns:
        ``{"session_id": str}``
    """
    raise NotImplementedError("metrics.start_session is planned for Phase 3")


def record_step(
    session_id: str,
    agent: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    model: str | None = None,
    duration_ms: int | None = None,
) -> dict:
    """Record per-agent token usage within a session.

    Returns:
        ``{"recorded": True}``
    """
    raise NotImplementedError("metrics.record_step is planned for Phase 3")


def end_session(session_id: str, status: str) -> dict:
    """Finalise a session and compute totals.

    Returns:
        ``{"session_id": str, "total_cost": float}``
    """
    raise NotImplementedError("metrics.end_session is planned for Phase 3")


def session_report(session_id: str) -> dict:
    """Generate a formatted session report.

    Returns:
        ``{"report": str}``
    """
    raise NotImplementedError("metrics.session_report is planned for Phase 3")


def trend(days: int = 30) -> dict:
    """Return cost/token trends over the last *days* days.

    Returns:
        ``{"daily_costs": [...], "avg_tokens": float, "trend": str}``
    """
    raise NotImplementedError("metrics.trend is planned for Phase 3")


def compare(session_id_a: str, session_id_b: str) -> dict:
    """Compare two sessions.

    Returns:
        ``{"diff": dict}``
    """
    raise NotImplementedError("metrics.compare is planned for Phase 3")
