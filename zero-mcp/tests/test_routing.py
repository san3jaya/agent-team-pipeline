"""Tests for ``tools.routing``."""

import pytest

from zero_mcp.tools.routing import recommend


class TestModelRecommend:
    @pytest.mark.parametrize(
        "agent, classification, expected_tier",
        [
            ("scope", "complex", "best"),
            ("scope", "standard", "best"),
            ("scope", "simple", "mid"),
            ("craft", "complex", "best"),
            ("craft", "trivial", "cheapest"),
            ("proof", "standard", "mid"),
            ("proof", "simple", "cheapest"),
            ("lens", "complex", "mid"),
            ("signal", "complex", "cheapest"),
            ("signal", "trivial", "cheapest"),
            ("zero", "complex", "best"),
            ("zero", "trivial", "cheapest"),
            ("trace", "complex", "best"),
        ],
    )
    def test_routing_rules(
        self, agent: str, classification: str, expected_tier: str
    ) -> None:
        result = recommend(agent, classification)
        assert result["tier"] == expected_tier
        assert "reason" in result

    def test_unknown_agent_falls_back_to_mid(self) -> None:
        result = recommend("unknown_agent", "standard")
        assert result["tier"] == "mid"

    def test_keyword_upgrade(self) -> None:
        result = recommend(
            "craft",
            "simple",
            task_description="refactor the authentication service",
        )
        # "refactor" is an upgrade keyword; craft+simple starts at "mid" → upgraded to "best"
        assert result["tier"] == "best"
        assert "refactor" in result["reason"]

    def test_keyword_downgrade(self) -> None:
        result = recommend(
            "scope",
            "standard",
            task_description="fix a typo in the readme",
        )
        # "typo" + "readme" are downgrade keywords; scope+standard starts at "best" → "mid"
        assert result["tier"] == "mid"

    def test_no_keyword_no_change(self) -> None:
        result = recommend(
            "craft", "standard", task_description="implement the feature"
        )
        assert result["tier"] == "best"

    def test_result_shape(self) -> None:
        result = recommend("proof", "complex")
        assert set(result.keys()) == {"tier", "reason"}
        assert result["tier"] in {"best", "mid", "cheapest"}
