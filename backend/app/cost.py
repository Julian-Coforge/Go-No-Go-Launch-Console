"""Cost of each pipeline step and each report, calculated in code.

Prices are USD per million tokens, from Anthropic's published API
pricing. Plain-code steps (limits, brief-by) use no model and cost $0.
"""

from collections.abc import Iterable
from typing import Optional

TOKENS_PER_MILLION = 1_000_000

# model id: (input $ per million tokens, output $ per million tokens)
PRICES_PER_MILLION: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-haiku-5-5": (0.10, 0.50),
}


def step_cost(model: Optional[str], input_tokens: int, output_tokens: int) -> float:
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Token counts cannot be negative")
    if model is None:
        return 0.0
    if model not in PRICES_PER_MILLION:
        raise ValueError(f"No price for model '{model}'; add it to PRICES_PER_MILLION")
    input_price, output_price = PRICES_PER_MILLION[model]
    return (input_tokens * input_price + output_tokens * output_price) / TOKENS_PER_MILLION


def report_cost(step_costs: Iterable[float]) -> float:
    return sum(step_costs, 0.0)
