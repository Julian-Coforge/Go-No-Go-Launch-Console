from typing import Optional

from fastapi import FastAPI

from app.llm import AnthropicClient, LLMClient


def create_app(llm: Optional[LLMClient] = None) -> FastAPI:
    app = FastAPI(title="Mission Control")
    app.state.llm = llm or AnthropicClient()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
