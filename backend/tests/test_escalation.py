"""Hybrid routing: keyword first, escalate to a second strategy when unsure.

A stub strategy stands in for the LLM so these tests never touch the network.
"""

from collections.abc import Sequence

import pytest

from app.agents import BaseAgent, create_agents
from app.models import RouteStatus
from app.router import FALLBACK_MESSAGE, QueryRouter
from app.router.strategies import RoutingStrategy, StrategyError, StrategyResult


class StubStrategy(RoutingStrategy):
    name = "stub"

    def __init__(self, pick: str | None = None, fail: bool = False) -> None:
        self.pick, self.fail, self.calls = pick, fail, 0

    def score(self, query: str, agents: Sequence[BaseAgent]) -> StrategyResult:
        self.calls += 1
        if self.fail:
            raise StrategyError("offline")
        return StrategyResult(
            scores={a.name: (10.0 if a.name == self.pick else 0.0) for a in agents},
            reason=f"stub picked {self.pick}",
        )


def router_with(stub: StubStrategy) -> QueryRouter:
    return QueryRouter(create_agents(), escalation=stub)


def test_confident_keyword_decision_does_not_escalate() -> None:
    stub = StubStrategy(pick="LinearAgent")
    decision = router_with(stub).decide("Show my open pull requests")
    assert decision.agent == "GitHubAgent"
    assert not decision.escalated
    assert stub.calls == 0


def test_keyword_miss_escalates() -> None:
    decision = router_with(StubStrategy(pick="LinearAgent")).decide("What am I supposed to be working on?")
    assert decision.status is RouteStatus.ROUTED
    assert decision.agent == "LinearAgent"
    assert decision.escalated
    assert decision.strategy == "stub"
    assert decision.reason == "stub picked LinearAgent"


def test_escalation_can_still_decline() -> None:
    result = router_with(StubStrategy(pick=None)).handle("What's the weather today?")
    assert result.message == FALLBACK_MESSAGE
    assert result.decision.escalated


def test_escalation_failure_keeps_keyword_decision() -> None:
    decision = router_with(StubStrategy(fail=True)).decide("show my issues")
    assert decision.status is RouteStatus.CLARIFY
    assert decision.strategy == "keyword"
    assert not decision.escalated


@pytest.mark.parametrize(
    ("query", "parts"),
    [
        ("Show my open PRs and my Linear tickets", ["Show my open PRs", "my Linear tickets"]),
        ("Did CI pass? Also what's in the sprint?", ["Did CI pass", "what's in the sprint"]),
        ("show my issues", ["show my issues"]),
    ],
)
def test_split_query(query: str, parts: list[str]) -> None:
    from app.router.splitter import split_query

    assert split_query(query) == parts


def test_parts_on_the_same_agent_stay_one_answer() -> None:
    result = QueryRouter(create_agents()).handle("Show my open pull requests and recent commits")
    assert result.decision.status is RouteStatus.ROUTED
    assert result.parts == []
