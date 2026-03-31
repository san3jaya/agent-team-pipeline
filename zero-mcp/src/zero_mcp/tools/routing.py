"""Rule-based model-tier recommendation for each agent × task classification."""

from __future__ import annotations

# ── Routing matrix ───────────────────────────────────────────────────────────
# Key = (agent, classification) → tier.
# Falls back to "mid" when no explicit rule matches.

_ROUTING_RULES: dict[tuple[str, str], str] = {
    # Scope — always needs best reasoning
    ("scope", "complex"): "best",
    ("scope", "standard"): "best",
    ("scope", "simple"): "mid",
    ("scope", "trivial"): "mid",
    # Craft
    ("craft", "complex"): "best",
    ("craft", "standard"): "best",
    ("craft", "simple"): "mid",
    ("craft", "trivial"): "cheapest",
    # Proof — execution, not reasoning
    ("proof", "complex"): "mid",
    ("proof", "standard"): "mid",
    ("proof", "simple"): "cheapest",
    ("proof", "trivial"): "cheapest",
    # Lens — code review
    ("lens", "complex"): "mid",
    ("lens", "standard"): "mid",
    ("lens", "simple"): "cheapest",
    ("lens", "trivial"): "cheapest",
    # Signal — git operations only
    ("signal", "complex"): "cheapest",
    ("signal", "standard"): "cheapest",
    ("signal", "simple"): "cheapest",
    ("signal", "trivial"): "cheapest",
    # Zero — orchestration
    ("zero", "complex"): "best",
    ("zero", "standard"): "best",
    ("zero", "simple"): "mid",
    ("zero", "trivial"): "cheapest",
    # Trace — standalone, deep analysis
    ("trace", "complex"): "best",
    ("trace", "standard"): "best",
    ("trace", "simple"): "mid",
    ("trace", "trivial"): "mid",
}

# Keywords in the task description that push towards a more capable model.
_UPGRADE_KEYWORDS: set[str] = {
    "refactor",
    "architecture",
    "security",
    "migration",
    "performance",
    "complex",
    "concurrency",
    "async",
    "database",
    "schema",
    "design",
}

# Keywords suggesting a cheaper model is fine.
_DOWNGRADE_KEYWORDS: set[str] = {
    "typo",
    "readme",
    "comment",
    "rename",
    "formatting",
    "lint",
    "style",
    "trivial",
    "boilerplate",
    "scaffold",
}


def recommend(
    agent: str,
    task_classification: str,
    task_description: str | None = None,
) -> dict:
    """Recommend a model tier for the given *agent* and *task_classification*.

    Args:
        agent: Agent name (``scope``, ``craft``, ``proof``, ``lens``,
            ``signal``, ``zero``, ``trace``).
        task_classification: One of ``trivial``, ``simple``, ``standard``,
            ``complex``.
        task_description: Optional free-text task description used for
            keyword-based adjustment.

    Returns:
        ``{"tier": "best"|"mid"|"cheapest", "reason": str}``
    """
    agent_lower = agent.lower().strip()
    classification_lower = task_classification.lower().strip()

    tier = _ROUTING_RULES.get((agent_lower, classification_lower), "mid")
    reason = f"Rule: {agent_lower}+{classification_lower} → {tier}"

    # Keyword heuristics from the task description
    if task_description:
        desc_lower = task_description.lower()
        tokens = set(desc_lower.split())

        upgrade_hits = tokens & _UPGRADE_KEYWORDS
        downgrade_hits = tokens & _DOWNGRADE_KEYWORDS

        if upgrade_hits and tier != "best":
            tier = _upgrade(tier)
            reason += f"; upgraded by keywords: {', '.join(sorted(upgrade_hits))}"
        elif downgrade_hits and tier != "cheapest":
            tier = _downgrade(tier)
            reason += f"; downgraded by keywords: {', '.join(sorted(downgrade_hits))}"

    return {"tier": tier, "reason": reason}


def _upgrade(tier: str) -> str:
    """Move a tier one step up."""
    if tier == "cheapest":
        return "mid"
    return "best"


def _downgrade(tier: str) -> str:
    """Move a tier one step down."""
    if tier == "best":
        return "mid"
    return "cheapest"
