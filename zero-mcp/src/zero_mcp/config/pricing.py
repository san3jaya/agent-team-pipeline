"""Model pricing tables and cost calculation utilities."""

# Prices per 1 million tokens (USD), as of early 2026.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4": {"input": 15.0, "cached_input": 1.50, "output": 75.0},
    "claude-sonnet-4": {"input": 3.0, "cached_input": 0.30, "output": 15.0},
    "claude-haiku-3.5": {"input": 0.80, "cached_input": 0.08, "output": 4.0},
    "gpt-4o": {"input": 2.50, "cached_input": 1.25, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "cached_input": 0.075, "output": 0.60},
    "gpt-5-mini": {"input": 0.20, "cached_input": 0.10, "output": 0.80},
    "o1": {"input": 15.0, "cached_input": 7.50, "output": 60.0},
}

# Fallback model used when the requested model is not in the pricing table.
_DEFAULT_MODEL = "claude-sonnet-4"


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    model: str = _DEFAULT_MODEL,
) -> float:
    """Return the estimated cost in USD for the given token usage.

    Args:
        input_tokens: Total input tokens (including cached).
        output_tokens: Total output tokens.
        cached_tokens: Tokens served from cache (subset of *input_tokens*).
        model: Model identifier — looked up in :data:`MODEL_PRICING`.
            Falls back to ``claude-sonnet-4`` if unknown.

    Returns:
        Cost in USD as a float.
    """
    pricing = MODEL_PRICING.get(model, MODEL_PRICING[_DEFAULT_MODEL])

    non_cached = max(0, input_tokens - cached_tokens)
    input_cost = non_cached * pricing["input"] / 1_000_000
    cached_cost = cached_tokens * pricing["cached_input"] / 1_000_000
    output_cost = output_tokens * pricing["output"] / 1_000_000

    return input_cost + cached_cost + output_cost
