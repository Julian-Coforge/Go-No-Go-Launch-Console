"""Cost is calculated in code from a price table (USD per million tokens)."""

import pytest

from app.cost import report_cost, step_cost


@pytest.mark.parametrize(
    ("model", "input_tokens", "output_tokens", "dollars"),
    [
        ("claude-opus-5-5", 1_000_000, 0, 4.00),
        ("claude-opus-5-5", 0, 1_000_000, 20.00),
        ("claude-opus-5-5", 2_000, 800, 0.024),
        ("claude-haiku-5-5", 1_000_000, 0, 0.10),
        ("claude-haiku-5-5", 0, 1_000_000, 0.50),
        ("claude-haiku-5-5", 1_000, 500, 0.00035),
    ],
    ids=["opus input", "opus output", "opus mixed", "haiku input", "haiku output", "haiku mixed"],
)
def test_model_step_cost_uses_the_price_table(model, input_tokens, output_tokens, dollars):
    assert step_cost(model, input_tokens, output_tokens) == pytest.approx(dollars)


def test_plain_code_step_costs_nothing():
    assert step_cost(None, 0, 0) == 0


def test_unknown_model_is_rejected():
    with pytest.raises(ValueError):
        step_cost("gpt-4o", 100, 100)


def test_negative_token_count_is_rejected():
    with pytest.raises(ValueError):
        step_cost("claude-haiku-5-5", -1, 0)


def test_report_cost_is_the_sum_of_its_steps():
    assert report_cost([0.024, 0.00035, 0]) == pytest.approx(0.02435)


def test_report_with_no_steps_costs_nothing():
    assert report_cost([]) == 0
