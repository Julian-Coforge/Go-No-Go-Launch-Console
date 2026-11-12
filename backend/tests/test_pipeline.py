"""The pipeline runs every step in order on a filed report: classify,
limits (code), brief-by (code), three checks, then draft and review. It
sets the status (never "approved"), records a trace card per step, and
adds up the cost in code."""

from pathlib import Path

import pytest

from app.cost import step_cost
from app.pipeline import run_pipeline
from app.schemas import ReportIn
from tests.fakes import APPROVE, FLAGGED, REJECT, pipeline_client

INJECTION_NOTE = (Path(__file__).parent / "fixtures" / "injection_note.txt").read_text().strip()

TRACE_STEPS = [
    "classify",
    "limits",
    "brief_by",
    "check_injection",
    "check_missing_details",
    "check_panic",
    "draft",
    "review",
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


async def run(report=None, **script):
    fake = pipeline_client(**script)
    return await run_pipeline(fake, report or make_report()), fake


async def test_clean_report_waits_for_approval():
    result, _ = await run()
    assert result.status == "pending_approval"


async def test_readings_within_limits_give_go():
    result, _ = await run()
    assert result.verdict == "go"


async def test_breached_limit_gives_no_go():
    result, _ = await run(make_report(wind_knots=30))
    assert result.verdict == "no_go"


async def test_violations_are_kept():
    result, _ = await run(make_report(wind_knots=30))
    assert [v.field for v in result.violations] == ["wind_knots"]


async def test_low_severity_gives_thirty_minute_brief_by():
    result, _ = await run()
    assert result.brief_by_minutes == 30


async def test_violation_forces_five_minute_brief_by():
    result, _ = await run(make_report(wind_knots=30))
    assert result.brief_by_minutes == 5


async def test_classifier_fallback_gives_five_minute_brief_by():
    result, _ = await run(classify="not json")
    assert result.brief_by_minutes == 5


async def test_classification_is_kept():
    result, _ = await run()
    assert result.classification.subsystem == "propulsion"


async def test_check_results_are_kept():
    result, _ = await run(injection=FLAGGED)
    assert result.checks.injection.flagged is True


async def test_flagged_injection_sends_report_to_review():
    result, _ = await run(injection=FLAGGED)
    assert result.status == "needs_review"


async def test_reviewer_never_approving_sends_report_to_review():
    result, _ = await run(reviews=[REJECT, REJECT, REJECT])
    assert result.status == "needs_review"


@pytest.mark.parametrize(
    "script",
    [
        pytest.param({}, id="clean"),
        pytest.param({"injection": FLAGGED}, id="injection"),
        pytest.param({"reviews": [REJECT, REJECT, REJECT]}, id="never-approved"),
    ],
)
async def test_pipeline_never_sets_approved(script):
    result, _ = await run(**script)
    assert result.status != "approved"


async def test_injection_note_with_breached_limit_stays_no_go():
    result, _ = await run(make_report(note=INJECTION_NOTE, wind_knots=30), injection=FLAGGED)
    assert result.verdict == "no_go"


async def test_injection_note_with_breached_limit_goes_to_review():
    result, _ = await run(make_report(note=INJECTION_NOTE, wind_knots=30), injection=FLAGGED)
    assert result.status == "needs_review"


async def test_injection_note_within_limits_keeps_go():
    result, _ = await run(make_report(note=INJECTION_NOTE), injection=FLAGGED)
    assert result.verdict == "go"


async def test_briefing_is_the_final_draft():
    result, _ = await run()
    assert result.briefing == "GO for launch. All readings within limits."


async def test_briefing_rounds_are_kept():
    result, _ = await run(reviews=[REJECT, APPROVE])
    assert len(result.rounds) == 2


async def test_draft_prompt_gets_the_code_verdict():
    _, fake = await run(make_report(wind_knots=30))
    draft = next(call for call in fake.calls if call.step == "draft")
    assert "Verdict (set by code): NO_GO" in draft.prompt


async def test_classifier_runs_first():
    _, fake = await run()
    assert fake.calls[0].step == "classify"


async def test_review_runs_last():
    _, fake = await run()
    assert fake.calls[-1].step == "review"


async def test_trace_has_a_card_for_every_step_in_order():
    result, _ = await run()
    assert [card.step for card in result.trace] == TRACE_STEPS


async def test_trace_has_a_draft_and_review_card_per_round():
    result, _ = await run(reviews=[REJECT, APPROVE])
    assert [card.step for card in result.trace][-4:] == ["draft", "review", "draft", "review"]


async def test_plain_code_steps_use_no_model():
    result, _ = await run()
    limits_card = result.trace[1]
    assert (limits_card.kind, limits_card.model, limits_card.cost_usd) == ("code", None, 0.0)


async def test_model_step_cost_is_calculated_in_code():
    result, _ = await run()
    assert result.trace[0].cost_usd == pytest.approx(step_cost("claude-haiku-5-5", 100, 50))


async def test_limits_card_summarises_the_verdict():
    result, _ = await run(make_report(wind_knots=30))
    assert "no_go" in result.trace[1].summary


async def test_total_cost_is_the_sum_of_the_trace():
    result, _ = await run(reviews=[REJECT, APPROVE])
    assert result.total_cost_usd == pytest.approx(sum(card.cost_usd for card in result.trace))


async def test_total_cost_for_a_one_round_report():
    # 4 Haiku calls at $0.000035 each + 2 Opus calls at $0.0014 each.
    result, _ = await run()
    assert result.total_cost_usd == pytest.approx(0.00294)


async def test_failed_model_step_is_marked_on_its_card():
    result, _ = await run(classify="not json")
    assert result.trace[0].fallback is True
