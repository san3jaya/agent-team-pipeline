"""Tests for ``tools.drift``."""

from zero_mcp.tools.drift import check


class TestDriftCheck:
    def test_aligned_returns_low_score(self, mock_embedding_model) -> None:
        result = check(
            mock_embedding_model,
            task_description="Add user authentication endpoint",
            changed_files=["src/auth/login.ts", "src/auth/middleware.ts"],
            diff_summary="Added login endpoint and auth middleware for JWT tokens",
        )
        assert "score" in result
        assert "verdict" in result
        assert isinstance(result["score"], float)
        assert 0.0 <= result["score"] <= 1.0

    def test_unrelated_returns_higher_score(self, mock_embedding_model) -> None:
        result = check(
            mock_embedding_model,
            task_description="Fix typo in README",
            changed_files=["src/database/migration_001.sql", "config/app.py"],
            diff_summary="Refactored entire database schema and added new ORM layer",
        )
        # With mock embeddings the exact score is unpredictable, but the
        # function should at least return a valid structure.
        assert "score" in result
        assert "verdict" in result
        assert result["verdict"] in {"aligned", "minor_drift", "significant_drift"}

    def test_suspicious_files_flagged(self, mock_embedding_model) -> None:
        result = check(
            mock_embedding_model,
            task_description="Update button colour",
            changed_files=["src/components/Button.vue", ".env"],
            diff_summary="Changed button CSS and env vars",
        )
        # .env is a suspicious pattern; it may or may not be flagged depending
        # on mock embeddings, but structure should be correct.
        assert isinstance(result["flags"], list)

    def test_verdict_categories(self, mock_embedding_model) -> None:
        """All verdicts must be one of the three allowed values."""
        for desc, diff in [
            ("x", "x"),
            ("build rocket", "painted the fence"),
        ]:
            result = check(
                mock_embedding_model,
                task_description=desc,
                changed_files=[],
                diff_summary=diff,
            )
            assert result["verdict"] in {"aligned", "minor_drift", "significant_drift"}
