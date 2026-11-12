"""Run every step on a filed report, in order:

1. classify (model)          4. three checks (model, at the same time)
2. limits (plain code)       5. draft and review (model, up to 3 rounds)
3. brief-by (plain code)

The verdict comes only from step 2. The status is needs_review when the note
has hidden instructions or the reviewer never approved, else
pending_approval. The pipeline never sets approved: only a person can.
Every step gets a trace card with its model, tokens and cost (in code).
"""

from typing import Literal, Optional

from pydantic import BaseModel

from app.brief_by import brief_by_minutes
from app.briefing import BRIEFING_MODEL, BriefingRound, run_briefing
from app.checks import ChecksResult, CheckResult, review_status, run_checks
from app.classify import ClassifyResult, classify_report
from app.cost import report_cost, step_cost
from app.limits import LimitResult, Verdict, Violation, check_limits
from app.llm import LLMClient
from app.schemas import ReportIn

PipelineStatus = Literal["needs_review", "pending_approval"]
# Only the approve route moves a report to "approved".
ReportStatus = Literal["needs_review", "pending_approval", "approved"]


class TraceStep(BaseModel):
    step: str
    kind: Literal["model", "code"]
    model: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    fallback: bool = False
    summary: str


class PipelineResult(BaseModel):
    verdict: Verdict
    violations: list[Violation]
    classification: ClassifyResult
    brief_by_minutes: int
    checks: ChecksResult
    rounds: list[BriefingRound]
    briefing: str
    reviewer_approved: bool
    status: PipelineStatus
    trace: list[TraceStep]
    total_cost_usd: float


class ReportOut(ReportIn, PipelineResult):
    """A filed report as saved: the input, its id and time, and the pipeline results."""

    id: int
    created_at: str
    status: ReportStatus
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None


def _model_card(
    step: str,
    model: Optional[str],
    input_tokens: int,
    output_tokens: int,
    summary: str,
    fallback: bool = False,
) -> TraceStep:
    return TraceStep(
        step=step,
        kind="model",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=step_cost(model, input_tokens, output_tokens),
        fallback=fallback,
        summary=summary,
    )


def _classify_card(result: ClassifyResult) -> TraceStep:
    summary = f"{result.subsystem} / {result.severity}"
    if result.fallback:
        summary += f" (fallback: {result.error})"
    return _model_card(
        "classify", result.model, result.input_tokens, result.output_tokens, summary, result.fallback
    )


def _limits_card(limits: LimitResult) -> TraceStep:
    found = "; ".join(v.message for v in limits.violations) or "all readings within limits"
    return TraceStep(step="limits", kind="code", summary=f"{limits.verdict}: {found}")


def _brief_by_card(minutes: int, severity: str, has_violation: bool) -> TraceStep:
    why = "a limit violation counts as high" if has_violation else f"severity {severity}"
    return TraceStep(step="brief_by", kind="code", summary=f"{minutes} minutes ({why})")


def _check_card(check: CheckResult) -> TraceStep:
    state = "flagged" if check.flagged else "clear"
    summary = f"{state}: {check.error or check.reason}"
    return _model_card(
        check.step, check.model, check.input_tokens, check.output_tokens, summary, check.fallback
    )


def _round_cards(round_: BriefingRound) -> list[TraceStep]:
    if not round_.draft and round_.error:
        return [
            _model_card(
                "draft", None, 0, 0, f"round {round_.round}: {round_.error}", fallback=True
            )
        ]
    draft = _model_card(
        "draft",
        round_.draft_model or BRIEFING_MODEL,
        round_.draft_input_tokens,
        round_.draft_output_tokens,
        f"round {round_.round}: {len(round_.draft)} characters drafted",
    )
    decision = "approved" if round_.approved else "not approved"
    review = _model_card(
        "review",
        round_.review_model,
        round_.review_input_tokens,
        round_.review_output_tokens,
        f"round {round_.round}: {decision}. {round_.error or round_.feedback}".strip(),
        round_.review_fallback,
    )
    return [draft, review]


async def run_pipeline(llm: LLMClient, report: ReportIn) -> PipelineResult:
    classification = await classify_report(llm, report)

    limits = check_limits(report.wind_knots, report.temp_c, report.fuel_pct)
    has_violation = bool(limits.violations)
    minutes = brief_by_minutes(classification.severity, has_violation)

    checks = await run_checks(llm, report)

    briefing = await run_briefing(
        llm,
        report=report,
        limits=limits,
        classification=classification,
        brief_by_minutes=minutes,
    )

    needs_review = review_status(checks) == "needs_review" or briefing.needs_human_review
    status: PipelineStatus = "needs_review" if needs_review else "pending_approval"

    trace = [
        _classify_card(classification),
        _limits_card(limits),
        _brief_by_card(minutes, classification.severity, has_violation),
        _check_card(checks.injection),
        _check_card(checks.missing_details),
        _check_card(checks.panic),
    ]
    for round_ in briefing.rounds:
        trace.extend(_round_cards(round_))

    return PipelineResult(
        verdict=limits.verdict,
        violations=limits.violations,
        classification=classification,
        brief_by_minutes=minutes,
        checks=checks,
        rounds=briefing.rounds,
        briefing=briefing.briefing,
        reviewer_approved=briefing.reviewer_approved,
        status=status,
        trace=trace,
        total_cost_usd=report_cost(card.cost_usd for card in trace),
    )
