"""Tests for ``tools.skills``."""

from pathlib import Path

from zero_mcp.tools.skills import discover


class TestSkillsDiscover:
    def test_detects_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{}")
        result = discover(str(tmp_path))
        names = [d["name"] for d in result["detected"]]
        assert "node" in names

    def test_detects_composer_json(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text("{}")
        result = discover(str(tmp_path))
        names = [d["name"] for d in result["detected"]]
        assert "php" in names

    def test_detects_cargo_toml(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").write_text("")
        result = discover(str(tmp_path))
        names = [d["name"] for d in result["detected"]]
        assert "rust" in names

    def test_detects_pyproject_toml(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("")
        result = discover(str(tmp_path))
        names = [d["name"] for d in result["detected"]]
        assert "python" in names

    def test_detects_skill_directory(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / ".cursor" / "rules"
        skill_dir.mkdir(parents=True)
        (skill_dir / "test.md").write_text("# Test skill\nDo the thing.")
        result = discover(str(tmp_path))
        tool_names = [d.get("source_tool") for d in result["detected"]]
        assert "cursor" in tool_names

    def test_detects_single_file_skill(self, tmp_path: Path) -> None:
        (tmp_path / ".windsurfrules").write_text("Some rules here.")
        result = discover(str(tmp_path))
        tool_names = [d.get("source_tool") for d in result["detected"]]
        assert "windsurf" in tool_names

    def test_returns_empty_for_empty_dir(self, tmp_path: Path) -> None:
        result = discover(str(tmp_path))
        assert result["detected"] == []
        assert result["snippets"] is None

    def test_returns_error_for_nonexistent_path(self) -> None:
        result = discover("/nonexistent/path/12345")
        assert "error" in result

    def test_snippets_with_query(self, tmp_path: Path, mock_embedding_model) -> None:
        skill_dir = tmp_path / ".ai" / "skills"
        skill_dir.mkdir(parents=True)
        (skill_dir / "testing.md").write_text(
            "# Testing\nAlways use pytest for Python tests."
        )

        result = discover(
            str(tmp_path),
            query="how to test python",
            embedding_model=mock_embedding_model,
        )
        assert result["snippets"] is not None
        assert len(result["snippets"]) >= 1
        assert "relevance" in result["snippets"][0]

    def test_multiple_markers(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "docker-compose.yml").write_text("")
        result = discover(str(tmp_path))
        names = [d["name"] for d in result["detected"]]
        assert "node" in names
        assert "docker" in names
