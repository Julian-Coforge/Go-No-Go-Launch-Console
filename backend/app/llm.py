"""The single interface every model call goes through.

The app uses AnthropicClient. Tests use FakeClient, so they run with no
network and no API key.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Union, runtime_checkable

from pydantic import BaseModel


class LLMResult(BaseModel):
    text: str
    input_tokens: int
    output_tokens: int
    model: str


@runtime_checkable
class LLMClient(Protocol):
    async def complete(
        self,
        *,
        step: str,
        model: str,
        system: str,
        prompt: str,
        schema: Optional[type[BaseModel]] = None,
    ) -> LLMResult: ...


@dataclass
class LLMCall:
    step: str
    model: str
    system: str
    prompt: str
    schema: Optional[type[BaseModel]]


Reply = Union[str, Exception]


class FakeClient:
    """Returns scripted replies per step, in order, and records every call."""

    def __init__(
        self,
        replies: Optional[dict[str, list[Reply]]] = None,
        *,
        input_tokens: int = 100,
        output_tokens: int = 50,
    ) -> None:
        self._replies = {step: list(queue) for step, queue in (replies or {}).items()}
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self.calls: list[LLMCall] = []

    async def complete(
        self,
        *,
        step: str,
        model: str,
        system: str,
        prompt: str,
        schema: Optional[type[BaseModel]] = None,
    ) -> LLMResult:
        self.calls.append(LLMCall(step, model, system, prompt, schema))
        queue = self._replies.get(step)
        if not queue:
            raise LookupError(f"FakeClient has no reply scripted for step '{step}'")
        reply = queue.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return LLMResult(
            text=reply,
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            model=model,
        )


class AnthropicClient:
    """Real Claude client. The SDK call is added with the pipeline steps (Phase 3)."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key

    async def complete(
        self,
        *,
        step: str,
        model: str,
        system: str,
        prompt: str,
        schema: Optional[type[BaseModel]] = None,
    ) -> LLMResult:
        raise NotImplementedError("AnthropicClient is implemented in Phase 3")
