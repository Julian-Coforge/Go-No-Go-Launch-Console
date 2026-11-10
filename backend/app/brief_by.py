"""Brief-by time, set in plain code from severity.

The Flight Director must be briefed within 5, 15 or 30 minutes for a
high, medium or low severity report. Any launch limit violation counts
as high, whatever severity the model gave.
"""

BRIEF_BY_MINUTES = {"high": 5, "medium": 15, "low": 30}


def brief_by_minutes(severity: str, has_violation: bool) -> int:
    if severity not in BRIEF_BY_MINUTES:
        raise ValueError(f"Unknown severity '{severity}'; expected high, medium or low")
    if has_violation:
        return BRIEF_BY_MINUTES["high"]
    return BRIEF_BY_MINUTES[severity]
