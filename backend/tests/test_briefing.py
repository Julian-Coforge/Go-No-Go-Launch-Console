"""Draft and review loop: the larger model drafts a briefing, a second call
reviews it, and the reviewer's feedback goes into the next draft. The loop
stops when the reviewer approves or after 3 rounds. The reviewer approving
is not a human approval; that only happens through the approve route."""

import json

import pytest

from app.briefing import (
    BRIEFING_MODEL,
    DRAFT,
    MAX_ROUNDS,
    REVIEW,
    ReviewReply,
    run_briefing,
)
from app.classify import ClassifyResult
from app.limits import check_limits
from app.llm import FakeClient
from app.schemas import ReportIn

APPROVE = json.dumps({"approved": True, "feedback": "Clear and accurate."})
REJECT_1 = json.dumps({"approved": False, "feedback": "Name the valve."})
REJECT_2 = json.dumps({"approved": False, "feedback": "State the brief-by time."})
REJECT_3 = json.dumps({"approved": False, "feedback": "Too long."})
DRAFTS = ["Draft one.", "Draft two.", "Draft three."]

INVALID_REVIEWS = [
    pytest.param("not json", id="malformed-json"),
    pytest.param('{"feedback": "no decision"}', id="missing-approved"),
    pytest.param('{"approved": "yes", "feedback": "?"}', id="approved-not-a-bool"),
]


def make_report(wind_knots=12.5):
    return ReportIn(
        name="Ada Lovelace",
        station="Pad 39A",
        wind_knots=wind_knots,
        temp_c=18.0,
        fuel_pct=99.0,
        note="Valve 3 pressure drifting low.",
    )


CLASSIFICATION = ClassifyResult(
    subsystem="propulsion", severity="medium", rationale="Valve drift.", fallback=False
)


async def brief(reviews, drafts=None, report=None, brief_by_minutes=15):
    report = report or make_report()
    fake = FakeClient({DRAFT: list(drafts or DRAFTS), REVIEW: list(reviews)})
    limits = check_limits(report.wind_knots, report.temp_c, report.fuel_pct)
    result = await run_briefing(
        fake,
        report=report,
        limits=limits,
        classification=CLASSIFICATION,
        brief_by_minutes=brief_by_minutes,
    )
    return result, fake


def calls_for(fake, step):
    return [call for call in fake.calls if call.step == step]


def test_loop_is_capped_at_three_rounds():
    assert MAX_ROUNDS == 3


async def test_approval_in_round_one_stops_after_one_round():
    result, _ = await brief([APPROVE])
    assert len(result.rounds) == 1


async def test_approval_in_round_two_stops_after_two_rounds():
    result, _ = await brief([REJECT_1, APPROVE])
    assert len(result.rounds) == 2


async def test_reviewer_who_never_approves_stops_at_three_rounds():
    result, _ = await brief([REJECT_1, REJECT_2, REJECT_3])
    assert len(result.rounds) == 3


async def test_never_approving_makes_exactly_three_drafts():
    _, fake = await brief([REJECT_1, REJECT_2, REJECT_3])
    assert len(calls_for(fake, DRAFT)) == 3


async def test_never_approving_makes_exactly_three_reviews():
    _, fake = await brief([REJECT_1, REJECT_2, REJECT_3])
    assert len(calls_for(fake, REVIEW)) == 3


async def test_rounds_are_numbered_from_one():
    result, _ = await brief([REJECT_1, REJECT_2, APPROVE])
    assert [r.round for r in result.rounds] == [1, 2, 3]


async def test_first_draft_has_no_feedback():
    _, fake = await brief([APPROVE])
    assert "Reviewer feedback" not in calls_for(fake, DRAFT)[0].prompt


async def test_reviewer_feedback_reaches_the_next_draft():
    _, fake = await brief([REJECT_1, APPROVE])
    assert "Name the valve." in calls_for(fake, DRAFT)[1].prompt


async def test_latest_feedback_reaches_the_third_draft():
    _, fake = await brief([REJECT_1, REJECT_2, APPROVE])
    assert "State the brief-by time." in calls_for(fake, DRAFT)[2].prompt


async def test_reviewer_sees_the_draft():
    _, fake = await brief([APPROVE])
    assert "Draft one." in calls_for(fake, REVIEW)[0].prompt


async def test_final_briefing_is_the_last_draft():
    result, _ = await brief([REJECT_1, APPROVE])
    assert result.briefing == "Draft two."


async def test_each_round_keeps_its_draft_and_feedback():
    result, _ = await brief([REJECT_1, APPROVE])
    assert (result.rounds[0].draft, result.rounds[0].feedback) == ("Draft one.", "Name the valve.")


async def test_reviewer_approval_is_recorded():
    result, _ = await brief([APPROVE])
    assert result.reviewer_approved is True


async def test_approved_briefing_does_not_need_human_review():
    result, _ = await brief([APPROVE])
    assert result.needs_human_review is False


async def test_unapproved_after_three_rounds_is_recorded():
    result, _ = await brief([REJECT_1, REJECT_2, REJECT_3])
    assert result.reviewer_approved is False


async def test_unapproved_after_three_rounds_needs_human_review():
    result, _ = await brief([REJECT_1, REJECT_2, REJECT_3])
    assert result.needs_human_review is True


async def test_draft_prompt_states_the_code_verdict():
    _, fake = await brief([APPROVE], report=make_report(wind_knots=30))
    assert "Verdict (set by code): NO_GO" in calls_for(fake, DRAFT)[0].prompt


async def test_draft_prompt_lists_the_violations():
    _, fake = await brief([APPROVE], report=make_report(wind_knots=30))
    assert "wind_knots 30 exceeds max 25" in calls_for(fake, DRAFT)[0].prompt


async def test_draft_prompt_states_the_brief_by_time():
    _, fake = await brief([APPROVE], brief_by_minutes=5)
    assert "Brief by: 5 minutes" in calls_for(fake, DRAFT)[0].prompt


async def test_draft_prompt_wraps_the_note_in_note_tags():
    _, fake = await brief([APPROVE])
    assert "<note>\nValve 3 pressure drifting low.\n</note>" in calls_for(fake, DRAFT)[0].prompt


async def test_both_steps_are_told_the_note_is_untrusted():
    _, fake = await brief([APPROVE])
    assert all("untrusted" in call.system for call in fake.calls)


async def test_both_steps_use_the_larger_model():
    _, fake = await brief([APPROVE])
    assert {call.model for call in fake.calls} == {BRIEFING_MODEL} == {"claude-opus-5-5"}


async def test_review_asks_for_the_review_schema():
    _, fake = await brief([APPROVE])
    assert calls_for(fake, REVIEW)[0].schema is ReviewReply


@pytest.mark.parametrize("reply", INVALID_REVIEWS)
async def test_invalid_review_counts_as_not_approved(reply):
    result, _ = await brief([reply, APPROVE])
    assert result.rounds[0].approved is False


@pytest.mark.parametrize("reply", INVALID_REVIEWS)
async def test_invalid_review_is_marked_as_fallback(reply):
    result, _ = await brief([reply, APPROVE])
    assert result.rounds[0].review_fallback is True


async def test_review_model_error_moves_on_to_the_next_round():
    result, _ = await brief([RuntimeError("API timeout"), APPROVE])
    assert len(result.rounds) == 2


async def test_draft_model_error_stops_the_loop():
    result, _ = await brief([APPROVE], drafts=[RuntimeError("API timeout")])
    assert len(result.rounds) == 1


async def test_draft_model_error_leaves_no_briefing():
    result, _ = await brief([APPROVE], drafts=[RuntimeError("API timeout")])
    assert result.briefing == ""


async def test_draft_model_error_needs_human_review():
    result, _ = await brief([APPROVE], drafts=[RuntimeError("API timeout")])
    assert result.needs_human_review is True


async def test_token_usage_is_recorded_per_round():
    result, _ = await brief([APPROVE])
    assert (result.rounds[0].draft_input_tokens, result.rounds[0].review_output_tokens) == (100, 50)
