"""AnthropicClient: the real Claude call, tested offline.

A stand-in for the Anthropic SDK records each request and returns a canned
response, so these tests never touch the network or need an API key.
"""

from types import SimpleNamespace
from typing import Literal

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.llm import AnthropicClient, MissingAPIKeyError, ModelRefusalError
from app.main import create_app


class Verdict(BaseModel):
    flagged: bool
    level: Literal["high", "low"]


def sdk_response(*blocks, input_tokens=120, output_tokens=40, stop_reason="end_turn"):
    return SimpleNamespace(
        content=list(blocks),
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
        stop_reason=stop_reason,
        model="claude-haiku-5-5",
    )


def text(value):
    return SimpleNamespace(type="text", text=value)


def thinking():
    return SimpleNamespace(type="thinking", thinking="", signature="sig")


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.requests = []

    async def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.response


class FakeSDK:
    """Mimics AsyncAnthropic: client.messages.create(**kwargs)."""

    def __init__(self, response=None):
        self.messages = FakeMessages(response or sdk_response(text("ok")))


async def call(sdk, *, schema=None, model="claude-haiku-5-5"):
    client = AnthropicClient(client=sdk)
    return await client.complete(
        step="classify", model=model, system="You classify.", prompt="<note>hi</note>",
        schema=schema,
    )


def sent(sdk):
    return sdk.messages.requests[0]


# --- the request ---


async def test_sends_the_model():
    sdk = FakeSDK()
    await call(sdk, model="claude-opus-5-5")
    assert sent(sdk)["model"] == "claude-opus-5-5"


async def test_sends_the_system_prompt():
    sdk = FakeSDK()
    await call(sdk)
    assert sent(sdk)["system"] == "You classify."


async def test_sends_the_prompt_as_one_user_message():
    sdk = FakeSDK()
    await call(sdk)
    assert sent(sdk)["messages"] == [{"role": "user", "content": "<note>hi</note>"}]


async def test_sets_a_max_tokens_limit():
    sdk = FakeSDK()
    await call(sdk)
    assert sent(sdk)["max_tokens"] > 0


async def test_schema_asks_for_json_schema_output():
    sdk = FakeSDK()
    await call(sdk, schema=Verdict)
    assert sent(sdk)["output_config"]["format"]["type"] == "json_schema"


async def test_schema_sends_the_model_fields():
    sdk = FakeSDK()
    await call(sdk, schema=Verdict)
    schema = sent(sdk)["output_config"]["format"]["schema"]
    assert set(schema["properties"]) == {"flagged", "level"}


async def test_no_schema_sends_no_output_format():
    sdk = FakeSDK()
    await call(sdk)
    assert "output_config" not in sent(sdk)


# --- the response ---


async def test_returns_the_reply_text():
    sdk = FakeSDK(sdk_response(text('{"flagged": false}')))
    assert (await call(sdk)).text == '{"flagged": false}'


async def test_skips_thinking_blocks():
    sdk = FakeSDK(sdk_response(thinking(), text("briefing")))
    assert (await call(sdk)).text == "briefing"


async def test_returns_input_tokens():
    sdk = FakeSDK(sdk_response(text("x"), input_tokens=321))
    assert (await call(sdk)).input_tokens == 321


async def test_returns_output_tokens():
    sdk = FakeSDK(sdk_response(text("x"), output_tokens=54))
    assert (await call(sdk)).output_tokens == 54


async def test_returns_the_model_that_was_asked_for():
    sdk = FakeSDK()
    assert (await call(sdk, model="claude-opus-5-5")).model == "claude-opus-5-5"


async def test_refusal_raises_an_error():
    sdk = FakeSDK(sdk_response(stop_reason="refusal"))
    with pytest.raises(ModelRefusalError):
        await call(sdk)


# --- the API key ---


async def test_missing_api_key_raises_a_clear_error():
    with pytest.raises(MissingAPIKeyError, match="ANTHROPIC_API_KEY"):
        await AnthropicClient().complete(
            step="classify", model="claude-haiku-5-5", system="s", prompt="p"
        )


def test_client_can_be_created_without_a_key():
    assert AnthropicClient() is not None


def test_missing_key_report_falls_back_to_needs_review(db_path, report):
    api = TestClient(create_app(db_path=db_path))
    assert api.post("/reports", json=report).json()["status"] == "needs_review"
