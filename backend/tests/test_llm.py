import pytest

from app.llm import AnthropicClient, FakeClient, LLMClient
from app.main import create_app


async def ask(fake: FakeClient, step: str = "classify", prompt: str = "p"):
    return await fake.complete(step=step, model="claude-haiku-5-5", system="s", prompt=prompt)


async def test_fake_returns_scripted_text():
    fake = FakeClient({"classify": ['{"severity": "high"}']})
    assert (await ask(fake)).text == '{"severity": "high"}'


async def test_fake_returns_replies_in_order():
    fake = FakeClient({"draft": ["first", "second"]})
    await ask(fake, step="draft")
    assert (await ask(fake, step="draft")).text == "second"


async def test_fake_records_each_prompt():
    fake = FakeClient({"draft": ["x"]})
    await ask(fake, step="draft", prompt="hello")
    assert fake.calls[0].prompt == "hello"


async def test_fake_reports_configured_token_counts():
    fake = FakeClient({"classify": ["x"]}, input_tokens=120, output_tokens=30)
    result = await ask(fake)
    assert (result.input_tokens, result.output_tokens) == (120, 30)


async def test_fake_reports_the_model_asked_for():
    fake = FakeClient({"classify": ["x"]})
    assert (await ask(fake)).model == "claude-haiku-5-5"


async def test_fake_raises_a_scripted_exception():
    fake = FakeClient({"classify": [RuntimeError("model down")]})
    with pytest.raises(RuntimeError):
        await ask(fake)


async def test_fake_raises_when_no_reply_is_scripted():
    with pytest.raises(LookupError):
        await ask(FakeClient({}))


def test_fake_client_fits_the_interface():
    assert isinstance(FakeClient({}), LLMClient)


def test_anthropic_client_fits_the_interface():
    assert isinstance(AnthropicClient(), LLMClient)


def test_app_uses_the_injected_client():
    fake = FakeClient({})
    assert create_app(llm=fake).state.llm is fake
