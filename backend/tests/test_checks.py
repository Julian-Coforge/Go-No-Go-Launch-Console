"""Three model checks on the note (hidden instructions, missing details,
panic) run at the same time. A failed check counts as flagged. A note with
hidden instructions sends the report to review but never changes the
verdict, which only the plain-code limit check sets."""

import asyncio
import json
from pathlib import Path

import pytest

from app.checks import (
    CHECKS_MODEL,
    INJECTION,
    MISSING_DETAILS,
    PANIC,
    review_status,
    run_checks,
)
from app.limits import check_limits
from app.llm import FakeClient
from app.schemas import ReportIn

INJECTION_NOTE = (Path(__file__).parent / "fixtures" / "injection_note.txt").read_text().strip()

CLEAN = json.dumps({"flagged": False, "reason": "Nothing found."})
FLAGGED = json.dumps({"flagged": True, "reason": "Found it."})
NOTHING_MISSING = json.dumps({"flagged": False, "reason": "Complete.", "missing": []})

INVALID_REPLIES = [
    pytest.param("not json", id="malformed-json"),
    pytest.param("", id="empty"),
    pytest.param('{"reason": "no flag given"}', id="missing-flagged"),
    pytest.param('{"flagged": "maybe", "reason": "?"}', id="flagged-not-a-bool"),
    pytest.param('{"flagged": "no", "reason": "?"}', id="flagged-as-the-word-no"),
]


def make_report(note="Valve 3 pressure nominal.", wind_knots=12.5):
    return ReportIn(
        name="Ada Lovelace",
        station="Pad 39A",
        wind_knots=wind_knots,
        temp_c=18.0,
        fuel_pct=99.0,
        note=note,
    )


def fake_with(injection=CLEAN, missing=NOTHING_MISSING, panic=CLEAN):
    return FakeClient({INJECTION: [injection], MISSING_DETAILS: [missing], PANIC: [panic]})


async def run_with(report=None, **replies):
    fake = fake_with(**replies)
    return await run_checks(fake, report or make_report()), fake


class OverlapClient(FakeClient):
    """Holds each call open briefly and records how many were open at once."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_flight = 0
        self.max_in_flight = 0

    async def complete(self, **kwargs):
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await asyncio.sleep(0.01)
        self.in_flight -= 1
        return await super().complete(**kwargs)


async def test_all_three_checks_are_called():
    _, fake = await run_with()
    assert sorted(call.step for call in fake.calls) == sorted([INJECTION, MISSING_DETAILS, PANIC])


async def test_checks_run_at_the_same_time():
    fake = OverlapClient({INJECTION: [CLEAN], MISSING_DETAILS: [NOTHING_MISSING], PANIC: [CLEAN]})
    await run_checks(fake, make_report())
    assert fake.max_in_flight == 3


async def test_checks_use_the_small_model():
    _, fake = await run_with()
    assert {call.model for call in fake.calls} == {CHECKS_MODEL} == {"claude-haiku-5-5"}


async def test_every_check_gets_the_note_inside_note_tags():
    report = make_report()
    _, fake = await run_with(report)
    assert all(f"<note>\n{report.note}\n</note>" in call.prompt for call in fake.calls)


async def test_every_check_is_told_the_note_is_untrusted():
    _, fake = await run_with()
    assert all("untrusted" in call.system for call in fake.calls)


async def test_every_check_asks_for_a_schema():
    _, fake = await run_with()
    assert all(call.schema is not None for call in fake.calls)


async def test_clean_reply_is_not_flagged():
    result, _ = await run_with()
    assert result.panic.flagged is False


async def test_flagged_reply_is_flagged():
    result, _ = await run_with(panic=FLAGGED)
    assert result.panic.flagged is True


async def test_reason_is_kept():
    result, _ = await run_with(panic=FLAGGED)
    assert result.panic.reason == "Found it."


async def test_missing_details_lists_what_is_missing():
    reply = json.dumps({"flagged": True, "reason": "Vague.", "missing": ["which valve"]})
    result, _ = await run_with(missing=reply)
    assert result.missing_details.missing == ["which valve"]


@pytest.mark.parametrize("reply", INVALID_REPLIES)
async def test_invalid_reply_counts_as_flagged(reply):
    result, _ = await run_with(panic=reply)
    assert result.panic.flagged is True


@pytest.mark.parametrize("reply", INVALID_REPLIES)
async def test_invalid_reply_is_marked_as_fallback(reply):
    result, _ = await run_with(panic=reply)
    assert result.panic.fallback is True


async def test_model_error_counts_as_flagged():
    result, _ = await run_with(injection=RuntimeError("API timeout"))
    assert result.injection.flagged is True


async def test_one_failed_check_does_not_stop_the_others():
    result, _ = await run_with(panic=RuntimeError("API timeout"))
    assert result.injection.flagged is False


async def test_token_usage_is_recorded_per_check():
    result, _ = await run_with()
    assert result.missing_details.input_tokens == 100


async def test_flagged_injection_sends_report_to_review():
    result, _ = await run_with(injection=FLAGGED)
    assert review_status(result) == "needs_review"


async def test_no_injection_waits_for_approval():
    result, _ = await run_with()
    assert review_status(result) == "pending_approval"


async def test_panic_alone_does_not_send_report_to_review():
    result, _ = await run_with(panic=FLAGGED)
    assert review_status(result) == "pending_approval"


async def test_failed_injection_check_sends_report_to_review():
    result, _ = await run_with(injection="not json")
    assert review_status(result) == "needs_review"


def test_fixture_note_contains_hidden_instructions():
    assert "Ignore all previous instructions" in INJECTION_NOTE


async def test_injection_note_with_breached_limit_goes_to_review():
    report = make_report(note=INJECTION_NOTE, wind_knots=30)
    result, _ = await run_with(report, injection=FLAGGED)
    assert review_status(result) == "needs_review"


async def test_injection_note_with_breached_limit_stays_no_go():
    report = make_report(note=INJECTION_NOTE, wind_knots=30)
    await run_with(report, injection=FLAGGED)
    assert check_limits(report.wind_knots, report.temp_c, report.fuel_pct).verdict == "no_go"


async def test_injection_note_within_limits_still_goes_to_review():
    report = make_report(note=INJECTION_NOTE)
    result, _ = await run_with(report, injection=FLAGGED)
    assert review_status(result) == "needs_review"


async def test_injection_note_within_limits_keeps_go_verdict():
    report = make_report(note=INJECTION_NOTE)
    await run_with(report, injection=FLAGGED)
    assert check_limits(report.wind_knots, report.temp_c, report.fuel_pct).verdict == "go"
