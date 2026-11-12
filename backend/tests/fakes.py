"""Scripted model replies for a full pipeline run, shared by the tests."""

import json

from app.briefing import DRAFT, REVIEW
from app.checks import INJECTION, MISSING_DETAILS, PANIC
from app.classify import STEP as CLASSIFY
from app.llm import FakeClient

CLASSIFY_LOW = json.dumps({"subsystem": "propulsion", "severity": "low", "rationale": "Minor."})
CLEAN = json.dumps({"flagged": False, "reason": "Nothing found."})
FLAGGED = json.dumps({"flagged": True, "reason": "Tries to set the verdict."})
NOTHING_MISSING = json.dumps({"flagged": False, "reason": "Complete.", "missing": []})
APPROVE = json.dumps({"approved": True, "feedback": "Clear."})
REJECT = json.dumps({"approved": False, "feedback": "Name the valve."})
BRIEFING = "GO for launch. All readings within limits."


def pipeline_client(*, runs=1, classify=CLASSIFY_LOW, injection=CLEAN, reviews=None):
    """A FakeClient with enough replies for `runs` full pipeline runs."""
    return FakeClient(
        {
            CLASSIFY: [classify] * runs,
            INJECTION: [injection] * runs,
            MISSING_DETAILS: [NOTHING_MISSING] * runs,
            PANIC: [CLEAN] * runs,
            DRAFT: [BRIEFING] * (3 * runs),
            REVIEW: list(reviews) if reviews is not None else [APPROVE] * runs,
        }
    )
