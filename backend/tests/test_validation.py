"""Report input validation: every field is required, text fields cannot be
blank or too long, and readings must be real numbers. Readings outside the
launch limits are still valid input; the limit check decides the verdict."""

import pytest
from pydantic import ValidationError

from app.schemas import NOTE_MAX_LEN, TEXT_MAX_LEN, ReportIn


def valid_report(**overrides):
    report = {
        "name": "Ada Lovelace",
        "station": "Pad 39A",
        "wind_knots": 12.5,
        "temp_c": 18.0,
        "fuel_pct": 99.0,
        "note": "All readings nominal.",
    }
    report.update(overrides)
    return report


def error_fields(excinfo):
    return {error["loc"][0] for error in excinfo.value.errors()}


def test_valid_report_is_accepted():
    assert ReportIn(**valid_report()).station == "Pad 39A"


@pytest.mark.parametrize(
    "field", ["name", "station", "wind_knots", "temp_c", "fuel_pct", "note"]
)
def test_missing_field_is_rejected(field):
    report = valid_report()
    del report[field]
    with pytest.raises(ValidationError):
        ReportIn(**report)


@pytest.mark.parametrize("field", ["name", "station", "note"])
def test_blank_text_is_rejected(field):
    with pytest.raises(ValidationError):
        ReportIn(**valid_report(**{field: "   "}))


def test_text_is_trimmed():
    assert ReportIn(**valid_report(name="  Ada Lovelace  ")).name == "Ada Lovelace"


@pytest.mark.parametrize("field", ["name", "station"])
def test_overlong_name_or_station_is_rejected(field):
    with pytest.raises(ValidationError):
        ReportIn(**valid_report(**{field: "x" * (TEXT_MAX_LEN + 1)}))


def test_overlong_note_is_rejected():
    with pytest.raises(ValidationError):
        ReportIn(**valid_report(note="x" * (NOTE_MAX_LEN + 1)))


def test_note_at_max_length_is_accepted():
    assert len(ReportIn(**valid_report(note="x" * NOTE_MAX_LEN)).note) == NOTE_MAX_LEN


@pytest.mark.parametrize("field", ["wind_knots", "temp_c", "fuel_pct"])
def test_non_numeric_reading_is_rejected(field):
    with pytest.raises(ValidationError):
        ReportIn(**valid_report(**{field: "calm"}))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_reading_is_rejected(value):
    with pytest.raises(ValidationError):
        ReportIn(**valid_report(temp_c=value))


def test_reading_outside_launch_limits_is_still_valid_input():
    assert ReportIn(**valid_report(wind_knots=40)).wind_knots == 40


def test_error_names_the_bad_field():
    with pytest.raises(ValidationError) as excinfo:
        ReportIn(**valid_report(fuel_pct="full"))
    assert error_fields(excinfo) == {"fuel_pct"}
