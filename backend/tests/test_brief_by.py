"""Brief-by time follows severity (high 5, medium 15, low 30 minutes).
Any launch limit violation counts as high."""

import pytest

from app.brief_by import brief_by_minutes


@pytest.mark.parametrize(
    ("severity", "minutes"),
    [("high", 5), ("medium", 15), ("low", 30)],
)
def test_brief_by_follows_severity_when_limits_are_met(severity, minutes):
    assert brief_by_minutes(severity, has_violation=False) == minutes


@pytest.mark.parametrize("severity", ["high", "medium", "low"])
def test_any_violation_counts_as_high(severity):
    assert brief_by_minutes(severity, has_violation=True) == 5


def test_unknown_severity_is_rejected():
    with pytest.raises(ValueError):
        brief_by_minutes("critical", has_violation=False)
