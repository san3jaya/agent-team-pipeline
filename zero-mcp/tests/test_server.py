"""Tests for ``server.py`` — tool registration and health/reset tools."""

import pytest

from zero_mcp.server import _dispatch, _TOOLS, list_tools


class TestToolRegistration:
    @pytest.mark.asyncio
    async def test_list_tools_returns_all_phase2_tools(self) -> None:
        tools = await list_tools()
        names = {t.name for t in tools}
        expected = {
            "patterns_search",
            "patterns_store",
            "patterns_prune",
            "drift_check",
            "model_recommend",
            "skills_discover",
            "project_index",
            "project_query",
            "project_dependencies",
            "health",
            "reset",
        }
        assert expected == names

    def test_tool_count(self) -> None:
        assert len(_TOOLS) == 11


class TestHealthTool:
    def test_health_returns_status(self, vector_store, monkeypatch) -> None:
        import zero_mcp.server as srv

        monkeypatch.setattr(srv, "_store", vector_store)
        monkeypatch.setattr(srv, "_model", vector_store.model)

        result = _dispatch("health", {})
        assert result["status"] == "ok"
        assert "version" in result
        assert "db_size" in result
        assert "pattern_count" in result


class TestResetTool:
    def test_reset_requires_confirm(self, vector_store, monkeypatch) -> None:
        import zero_mcp.server as srv

        monkeypatch.setattr(srv, "_store", vector_store)
        monkeypatch.setattr(srv, "_model", vector_store.model)

        result = _dispatch("reset", {"confirm": False})
        assert result["reset"] is False

    def test_reset_clears_data(self, vector_store, monkeypatch) -> None:
        import zero_mcp.server as srv

        monkeypatch.setattr(srv, "_store", vector_store)
        monkeypatch.setattr(srv, "_model", vector_store.model)

        # Add some data first
        vector_store.store_pattern("test", "ctx", "app", "out")
        assert vector_store.get_pattern_count() == 1

        result = _dispatch("reset", {"confirm": True})
        assert result["reset"] is True
        assert vector_store.get_pattern_count() == 0


class TestUnknownTool:
    def test_unknown_tool_returns_error(self, vector_store, monkeypatch) -> None:
        import zero_mcp.server as srv

        monkeypatch.setattr(srv, "_store", vector_store)
        monkeypatch.setattr(srv, "_model", vector_store.model)

        result = _dispatch("nonexistent_tool", {})
        assert "error" in result
