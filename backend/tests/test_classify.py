"""The classifier asks the small model for a subsystem and severity, checks
the reply in code, and falls back safely (other / high) when the reply is
invalid or the model call fails."""

import json

import pytest

from app.brief_by import brief_by_minutes
from app.classify import CLASSIFY_MODEL, Classification, classify_report
from app.llm import FakeClient
from app.schemas import ReportIn

REPORT = ReportIn(
    name="Ada Lovelace",
    station="Pad 39A",
    wind_knots=12.5,
    temp_c=18.0,
    fuel_pct=99.0,
    note="Valve 3 pressure is drifting low.",
)

VALID_REPLY = json.dumps(
    {"subsystem": "propulsion", "severity": "medium", "rationale": "Valve pressure drift."}
)

INVALID_REPLIES = [
    pytest.param("not json at all", id="malformed-json"),
    pytest.param("", id="empty"),
    pytest.param('{"subsystem": "propulsion", "severity": "critical"}', id="unknown-severity"),
    pytest.param('{"subsystem": "plumbing", "severity": "low"}', id="unknown-subsystem"),
    pytest.param('{"subsystem": "propulsion"}', id="missing-severity"),
    pytest.param('["propulsion", "low"]', id="not-an-object"),
]


async def classify_with(reply):
    fake = FakeClient({"classify": [reply]})
    return await classify_report(fake, REPORT), fake


async def test_valid_reply_gives_subsystem():
    result, _ = await classify_with(VALID_REPLY)
    assert result.subsystem == "propulsion"


async def test_valid_reply_gives_severity():
    result, _ = await classify_with(VALID_REPLY)
    assert result.severity == "medium"


async def test_valid_reply_keeps_rationale():
    result, _ = await classify_with(VALID_REPLY)
    assert result.rationale == "Valve pressure drift."


async def test_valid_reply_is_not_a_fallback():
    result, _ = await classify_with(VALID_REPLY)
    assert result.fallback is False


@pytest.mark.parametrize("reply", INVALID_REPLIES)
async def test_invalid_reply_falls_back_to_other(reply):
    result, _ = await classify_with(reply)
    assert result.subsystem == "other"


@pytest.mark.parametrize("reply", INVALID_REPLIES)
async def test_invalid_reply_falls_back_to_high(reply):
    result, _ = await classify_with(reply)
    assert result.severity == "high"


@pytest.mark.parametrize("reply", INVALID_REPLIES)
async def test_invalid_reply_is_marked_as_fallback(reply):
    result, _ = await classify_with(reply)
    assert result.fallback is True


async def test_fallback_records_why():
    result, _ = await classify_with("not json at all")
    assert result.error


async def test_model_error_falls_back_to_high():
    result, _ = await classify_with(RuntimeError("API timeout"))
    assert result.severity == "high"


async def test_model_error_is_marked_as_fallback():
    result, _ = await classify_with(RuntimeError("API timeout"))
    assert result.fallback is True


async def test_fallback_severity_gives_five_minute_brief_by():
    result, _ = await classify_with('{"severity": "critical"}')
    assert brief_by_minutes(result.severity, has_violation=False) == 5


async def test_uses_the_small_model():
    _, fake = await classify_with(VALID_REPLY)
    assert fake.calls[0].model == CLASSIFY_MODEL == "claude-haiku-5-5"


async def test_asks_for_the_classification_schema():
    _, fake = await classify_with(VALID_REPLY)
    assert fake.calls[0].schema is Classification


async def test_note_is_wrapped_in_note_tags():
    _, fake = await classify_with(VALID_REPLY)
    assert f"<note>\n{REPORT.note}\n</note>" in fake.calls[0].prompt


async def test_system_prompt_marks_the_note_as_untrusted():
    _, fake = await classify_with(VALID_REPLY)
    assert "untrusted" in fake.calls[0].system


async def test_token_usage_is_recorded():
    result, _ = await classify_with(VALID_REPLY)
    assert (result.input_tokens, result.output_tokens) == (100, 50)


async def test_model_error_records_no_tokens():
    result, _ = await classify_with(RuntimeError("API timeout"))
    assert result.input_tokens == 0
