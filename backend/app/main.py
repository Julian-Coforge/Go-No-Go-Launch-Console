import os
from pathlib import Path
from typing import Optional, Union

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.llm import AnthropicClient, LLMClient
from app.pipeline import ReportOut, run_pipeline
from app.schemas import ApproveIn, ReportIn
from app.store import ReportStore

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mission_control.db"


def create_app(
    llm: Optional[LLMClient] = None,
    db_path: Union[str, Path, None] = None,
) -> FastAPI:
    app = FastAPI(title="Mission Control")
    app.state.llm = llm or AnthropicClient()
    app.state.store = ReportStore(
        db_path or os.environ.get("MISSION_CONTROL_DB", DEFAULT_DB_PATH)
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # One entry per bad field, e.g. {"field": "fuel_pct", "message": "..."}.
        errors = [
            {"field": ".".join(str(part) for part in error["loc"][1:]), "message": error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"errors": errors})

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/reports", status_code=201)
    async def file_report(report: ReportIn) -> ReportOut:
        result = await run_pipeline(app.state.llm, report)
        return app.state.store.add(report, result)

    @app.get("/reports")
    def list_reports() -> list[ReportOut]:
        return app.state.store.list_all()

    def find_report(report_id: int) -> ReportOut:
        saved = app.state.store.get(report_id)
        if saved is None:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
        return saved

    @app.get("/reports/{report_id}")
    def get_report(report_id: int) -> ReportOut:
        return find_report(report_id)

    @app.post("/reports/{report_id}/approve")
    def approve_report(report_id: int, approval: ApproveIn) -> ReportOut:
        """The only way a report becomes approved: a named person approves it."""
        approved = app.state.store.approve(report_id, approval.approver_name)
        if approved is None:
            current = find_report(report_id)
            raise HTTPException(
                status_code=409,
                detail=f"Report {report_id} is already {current.status} by {current.approved_by}",
            )
        return approved

    return app
