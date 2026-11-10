"""Launch limits, checked in plain code. No model is ever involved.

A reading outside its limit makes the verdict no_go. The limits are
inclusive: wind of exactly 25 knots is still go.
"""

from typing import Literal

from pydantic import BaseModel

WIND_MAX_KNOTS = 25
TEMP_MIN_C = 4
FUEL_MIN_PCT = 98
FUEL_MAX_PCT = 100

Verdict = Literal["go", "no_go"]


class Violation(BaseModel):
    field: str
    value: float
    limit: float
    message: str


class LimitResult(BaseModel):
    verdict: Verdict
    violations: list[Violation]


def _above(field: str, value: float, limit: float) -> Violation:
    return Violation(field=field, value=value, limit=limit, message=f"{field} {value:g} exceeds max {limit:g}")


def _below(field: str, value: float, limit: float) -> Violation:
    return Violation(field=field, value=value, limit=limit, message=f"{field} {value:g} is below min {limit:g}")


def check_limits(wind_knots: float, temp_c: float, fuel_pct: float) -> LimitResult:
    violations: list[Violation] = []

    if wind_knots > WIND_MAX_KNOTS:
        violations.append(_above("wind_knots", wind_knots, WIND_MAX_KNOTS))
    if temp_c < TEMP_MIN_C:
        violations.append(_below("temp_c", temp_c, TEMP_MIN_C))
    if fuel_pct < FUEL_MIN_PCT:
        violations.append(_below("fuel_pct", fuel_pct, FUEL_MIN_PCT))
    elif fuel_pct > FUEL_MAX_PCT:
        violations.append(_above("fuel_pct", fuel_pct, FUEL_MAX_PCT))

    return LimitResult(verdict="no_go" if violations else "go", violations=violations)
