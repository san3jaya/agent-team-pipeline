"""Tests for ``tools.patterns`` wrappers."""

from zero_mcp.memory.store import VectorStore
from zero_mcp.tools import patterns


class TestPatternTools:
    def test_store_returns_id(self, vector_store: VectorStore) -> None:
        result = patterns.store(
            vector_store,
            name="test-pattern",
            context="testing",
            approach="write tests",
            outcome="success",
        )
        assert result["stored"] is True
        assert isinstance(result["id"], int)

    def test_search_finds_stored_pattern(self, vector_store: VectorStore) -> None:
        patterns.store(
            vector_store,
            name="laravel-pest",
            context="Laravel project with Pest testing",
            approach="Use pest --parallel",
            outcome="Tests 4x faster",
        )
        result = patterns.search(vector_store, query="Laravel Pest parallel testing", min_score=-1.0)
        assert len(result["results"]) >= 1
        assert result["results"][0]["name"] == "laravel-pest"

    def test_search_empty_store(self, vector_store: VectorStore) -> None:
        result = patterns.search(vector_store, query="anything")
        assert result["results"] == []

    def test_prune_returns_counts(self, vector_store: VectorStore) -> None:
        patterns.store(vector_store, name="a", context="c", approach="a", outcome="o")
        result = patterns.prune(vector_store, max_age_days=0)
        assert "pruned" in result
        assert "remaining" in result

    def test_project_scoped_store_and_search(self, vector_store: VectorStore) -> None:
        patterns.store(
            vector_store,
            name="project-a-pattern",
            context="specific to project A",
            approach="do X",
            outcome="ok",
            project="project-a",
        )
        result = patterns.search(
            vector_store, query="specific to project A", project="project-a", min_score=-1.0
        )
        assert len(result["results"]) >= 1
