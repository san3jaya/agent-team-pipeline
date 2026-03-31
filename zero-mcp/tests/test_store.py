"""Tests for ``memory.store.VectorStore``."""

from zero_mcp.memory.store import VectorStore


class TestVectorStore:
    def test_store_and_search_pattern(self, vector_store: VectorStore) -> None:
        vector_store.store_pattern(
            name="vue-options-api",
            context="Vue 2 project using Options API",
            approach="Use mixins for shared logic",
            outcome="Success",
        )
        results = vector_store.search_patterns("Vue 2 Options API mixins", min_score=-1.0)
        assert len(results) >= 1
        assert results[0]["name"] == "vue-options-api"
        # Score may be negative with mock embeddings (random vectors)
        assert -1.0 <= results[0]["score"] <= 1.0

    def test_pattern_count(self, vector_store: VectorStore) -> None:
        assert vector_store.get_pattern_count() == 0
        vector_store.store_pattern("a", "ctx", "app", "out")
        assert vector_store.get_pattern_count() == 1
        vector_store.store_pattern("b", "ctx", "app", "out")
        assert vector_store.get_pattern_count() == 2

    def test_search_returns_empty_when_no_patterns(
        self, vector_store: VectorStore
    ) -> None:
        results = vector_store.search_patterns("anything")
        assert results == []

    def test_search_respects_project_filter(self, vector_store: VectorStore) -> None:
        vector_store.store_pattern("p1", "c", "a", "o", project="projectA")
        vector_store.store_pattern("p2", "c", "a", "o", project="projectB")

        results = vector_store.search_patterns("c a", project="projectA", min_score=-1.0)
        project_names = {r["name"] for r in results}
        # Should include p1 (projectA) but could include p2 only if project is None
        # With project="projectA", query returns project=projectA OR project IS NULL
        assert "p1" in project_names

    def test_prune_removes_old_unmatched(self, vector_store: VectorStore) -> None:
        vector_store.store_pattern("old", "c", "a", "o")
        # Force the created_at to be old
        vector_store.conn.execute(
            "UPDATE patterns SET created_at = datetime('now', '-100 days') WHERE name = 'old'"
        )
        vector_store.conn.commit()

        pruned = vector_store.prune(max_age_days=90)
        assert pruned == 1
        assert vector_store.get_pattern_count() == 0

    def test_prune_keeps_matched_patterns(self, vector_store: VectorStore) -> None:
        vector_store.store_pattern("popular", "c", "a", "o")
        vector_store.conn.execute(
            "UPDATE patterns SET created_at = datetime('now', '-100 days'), "
            "match_count = 5 WHERE name = 'popular'"
        )
        vector_store.conn.commit()

        pruned = vector_store.prune(max_age_days=90)
        assert pruned == 0
        assert vector_store.get_pattern_count() == 1

    def test_db_size_positive_after_insert(self, vector_store: VectorStore) -> None:
        vector_store.store_pattern("x", "c", "a", "o")
        assert vector_store.get_db_size() > 0

    def test_tables_exist(self, vector_store: VectorStore) -> None:
        tables = {
            row[0]
            for row in vector_store.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        expected = {
            "patterns",
            "sessions",
            "steps",
            "mcp_calls",
            "project_files",
            "file_exports",
            "file_imports",
        }
        assert expected.issubset(tables)
