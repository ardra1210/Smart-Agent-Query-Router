"""LLMStrategy request/response handling, with a fake Anthropic client (no network)."""

import json
from types import SimpleNamespace

import pytest

anthropic = pytest.importorskip("anthropic")

from app.agents import create_agents  # noqa: E402
from app.router.strategies import StrategyError  # noqa: E402
from app.router.strategies.llm import LLMStrategy, verdict_to_result  # noqa: E402

NAMES = ["GitHubAgent", "LinearAgent"]


class FakeClient:
    """Mimics client.beta.messages.create and records the request."""

    def __init__(self, verdict: dict | None = None, stop_reason: str = "end_turn") -> None:
        self.verdict, self.stop_reason, self.request = verdict, stop_reason, None
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.request = kwargs
        content = [SimpleNamespace(type="text", text=json.dumps(self.verdict))] if self.verdict else []
        return SimpleNamespace(stop_reason=self.stop_reason, content=content)


def test_verdict_for_one_agent() -> None:
    result = verdict_to_result({"agent": "LinearAgent", "candidates": [], "reason": "work items"}, NAMES)
    assert result.scores == {"GitHubAgent": 0.0, "LinearAgent": 10.0}
    assert result.reason == "work items"


def test_verdict_none_scores_nothing() -> None:
    assert set(verdict_to_result({"agent": "none", "candidates": []}, NAMES).scores.values()) == {0.0}


def test_verdict_ambiguous_scores_candidates_equally() -> None:
    scores = verdict_to_result({"agent": "ambiguous", "candidates": NAMES}, NAMES).scores
    assert scores == {"GitHubAgent": 10.0, "LinearAgent": 10.0}


def test_unknown_agent_is_rejected() -> None:
    with pytest.raises(StrategyError):
        verdict_to_result({"agent": "SlackAgent", "candidates": []}, NAMES)


def test_request_shape() -> None:
    client = FakeClient({"agent": "GitHubAgent", "candidates": [], "reason": "code review"})
    result = LLMStrategy(client=client).score("Has anyone approved my code changes?", create_agents())
    assert result.scores["GitHubAgent"] == 10.0

    request = client.request
    assert request["model"] == "claude-opus-5-5"
    assert request["output_config"]["format"]["schema"]["properties"]["agent"]["enum"] == [*NAMES, "none", "ambiguous"]
    assert "GitHubAgent" in request["system"] and "LinearAgent" in request["system"]
    assert request["messages"] == [{"role": "user", "content": "Has anyone approved my code changes?"}]


@pytest.mark.parametrize(
    "error",
    [
        TypeError('"Could not resolve authentication method. Expected one of api_key, auth_token..."'),
        anthropic.CredentialsError("Config file not found"),
    ],
)
def test_missing_credentials_degrade_to_strategy_error(error: Exception) -> None:
    client = FakeClient()

    def fail(**kwargs):
        raise error

    client.beta.messages.create = fail
    with pytest.raises(StrategyError):
        LLMStrategy(client=client).score("What am I supposed to be working on?", create_agents())


def test_refusal_raises_strategy_error() -> None:
    with pytest.raises(StrategyError):
        LLMStrategy(client=FakeClient(stop_reason="refusal")).score("anything", create_agents())
