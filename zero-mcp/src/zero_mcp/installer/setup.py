"""Auto-installer: detect AI tools, copy agents, register MCP server.

.. note:: Stub implementation for Phase 5.
"""

from __future__ import annotations


def install(copy_agents: bool = True, register_mcp: bool = True) -> dict:
    """Run the full installation: detect tools, copy agents, register MCP.

    Returns:
        ``{"detected_tools": [...], "registered": [...], "errors": [...]}``
    """
    raise NotImplementedError("installer.install is planned for Phase 5")


def detect_installed_tools() -> list[str]:
    """Detect which AI tools are installed on this system.

    Returns:
        List of tool identifiers (e.g. ``["opencode", "cursor"]``).
    """
    raise NotImplementedError("installer.detect_installed_tools is planned for Phase 5")
