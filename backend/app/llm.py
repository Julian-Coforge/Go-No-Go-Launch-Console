"""The single interface every model call goes through.

The app uses AnthropicClient. Tests use FakeClient, so they run with no
network and no API key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional, Protocol, Union, runtime_checkable

import anthropic
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


class MissingAPIKeyError(RuntimeError):
    """No Anthropic API key is set, so no real model call can be made."""


class ModelRefusalError(RuntimeError):
    """The model declined to answer (stop_reason "refusal")."""


MAX_TOKENS = 16000


class AnthropicClient:
    """Real Claude client using the official anthropic SDK.

    The SDK client is created on the first call, so the app can start with
    no API key. A call without a key raises MissingAPIKeyError, and the
    pipeline treats that like any other model error: a safe fallback.
    Tests pass `client=` to swap in a stand-in for AsyncAnthropic.
    """

    def __init__(self, api_key: Optional[str] = None, *, client: Any = None) -> None:
        self._api_key = api_key
        self._client = client

    def _sdk(self) -> Any:
        if self._client is None:
            key = self._api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise MissingAPIKeyError(
                    "ANTHROPIC_API_KEY is not set, so the model step cannot run"
                )
            self._client = anthropic.AsyncAnthropic(api_key=key)
        return self._client

    async def complete(
        self,
        *,
        step: str,
        model: str,
        system: str,
        prompt: str,
        schema: Optional[type[BaseModel]] = None,
    ) -> LLMResult:
        request: dict[str, Any] = {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        if schema is not None:
            request["output_config"] = {
                "format": {
                    "type": "json_schema",
                    "schema": anthropic.transform_schema(schema),
                }
            }
        response = await self._sdk().messages.create(**request)
        if response.stop_reason == "refusal":
            raise ModelRefusalError(f"{model} declined the {step} step")
        text = "".join(block.text for block in response.content if block.type == "text")
        return LLMResult(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=model,
        )
