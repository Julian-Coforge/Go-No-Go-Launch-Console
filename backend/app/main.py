import os
from pathlib import Path
from typing import Optional, Union

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.llm import AnthropicClient, LLMClient
from app.schemas import ReportIn, ReportOut
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
    def file_report(report: ReportIn) -> ReportOut:
        return app.state.store.add(report)

    @app.get("/reports")
    def list_reports() -> list[ReportOut]:
        return app.state.store.list_all()

    @app.get("/reports/{report_id}")
    def get_report(report_id: int) -> ReportOut:
        saved = app.state.store.get(report_id)
        if saved is None:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
        return saved

    return app
