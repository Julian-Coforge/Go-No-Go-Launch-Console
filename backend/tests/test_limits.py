"""Launch limits are plain code: wind <= 25 kn, temp >= 4 C, fuel 98-100 %."""

import ast
import inspect

import pytest

from app import limits
from app.limits import check_limits

SAFE = {"wind_knots": 10, "temp_c": 15, "fuel_pct": 99}


def readings(**changes):
    return {**SAFE, **changes}


@pytest.mark.parametrize(
    "changes",
    [
        {"wind_knots": 25},
        {"temp_c": 4},
        {"fuel_pct": 98},
        {"fuel_pct": 100},
    ],
    ids=["wind exactly 25", "temp exactly 4", "fuel exactly 98", "fuel exactly 100"],
)
def test_reading_exactly_on_its_limit_is_go(changes):
    assert check_limits(**readings(**changes)).verdict == "go"


@pytest.mark.parametrize(
    "changes",
    [
        {"wind_knots": 25.01},
        {"temp_c": 3.99},
        {"fuel_pct": 97.99},
        {"fuel_pct": 100.01},
    ],
    ids=["wind 25.01", "temp 3.99", "fuel 97.99", "fuel 100.01"],
)
def test_reading_just_past_its_limit_is_no_go(changes):
    assert check_limits(**readings(**changes)).verdict == "no_go"


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"wind_knots": 25.01}, "wind_knots"),
        ({"temp_c": 3.99}, "temp_c"),
        ({"fuel_pct": 97.99}, "fuel_pct"),
        ({"fuel_pct": 100.01}, "fuel_pct"),
    ],
    ids=["wind", "temp", "fuel low", "fuel high"],
)
def test_breach_is_reported_against_its_field(changes, field):
    result = check_limits(**readings(**changes))
    assert [v.field for v in result.violations] == [field]


def test_readings_within_limits_have_no_violations():
    assert check_limits(**SAFE).violations == []


def test_every_breached_reading_is_reported_in_field_order():
    result = check_limits(wind_knots=30, temp_c=2, fuel_pct=50)
    assert [v.field for v in result.violations] == ["wind_knots", "temp_c", "fuel_pct"]


def test_violation_records_the_reading_and_its_limit():
    violation = check_limits(**readings(wind_knots=27)).violations[0]
    assert (violation.value, violation.limit) == (27, 25)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"wind_knots": 27}, "wind_knots 27 exceeds max 25"),
        ({"temp_c": 3.5}, "temp_c 3.5 is below min 4"),
        ({"fuel_pct": 97}, "fuel_pct 97 is below min 98"),
        ({"fuel_pct": 101}, "fuel_pct 101 exceeds max 100"),
    ],
    ids=["wind", "temp", "fuel low", "fuel high"],
)
def test_violation_message_is_readable(changes, message):
    assert check_limits(**readings(**changes)).violations[0].message == message


def test_limits_module_imports_no_model_code():
    tree = ast.parse(inspect.getsource(limits))
    imported = {
        name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for name in ([node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names])
    }
    assert imported.isdisjoint({"anthropic", "app.llm", "llm"})
