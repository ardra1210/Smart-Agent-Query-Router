import pytest

from app.agents import BaseAgent, capability, create_agents
from app.agents.base import Reply
from app.models import RouteStatus
from app.router import FALLBACK_MESSAGE, QueryRouter


@pytest.fixture(scope="module")
def router() -> QueryRouter:
    return QueryRouter(create_agents())


# The three examples given in the task brief.
def test_routes_pull_requests_to_github(router: QueryRouter) -> None:
    result = router.handle("Show my open pull requests")
    assert result.decision.status is RouteStatus.ROUTED
    assert result.decision.agent == "GitHubAgent"
    assert result.response.capability == "open_pull_requests"


def test_routes_assigned_issues_to_linear(router: QueryRouter) -> None:
    result = router.handle("What issues are assigned to me?")
    assert result.decision.agent == "LinearAgent"
    assert result.response.capability == "assigned_issues"


def test_out_of_scope_question_falls_back(router: QueryRouter) -> None:
    result = router.handle("What's the weather today?")
    assert result.decision.status is RouteStatus.FALLBACK
    assert result.message == FALLBACK_MESSAGE
    assert result.response is None


@pytest.mark.parametrize("query", ["", "   ", "?!"])
def test_blank_or_punctuation_only_query_falls_back(router: QueryRouter, query: str) -> None:
    assert router.handle(query).message == FALLBACK_MESSAGE


def test_routing_is_case_and_punctuation_insensitive(router: QueryRouter) -> None:
    assert router.decide("SHOW MY OPEN PRS!!!").agent == "GitHubAgent"


def test_ambiguous_query_asks_for_clarification(router: QueryRouter) -> None:
    decision = router.decide("show my issues")
    assert decision.status is RouteStatus.CLARIFY
    assert set(decision.candidates) == {"GitHubAgent", "LinearAgent"}


def test_naming_the_tool_resolves_ambiguity(router: QueryRouter) -> None:
    assert router.decide("show my GitHub issues").agent == "GitHubAgent"
    assert router.decide("show my Linear issues").agent == "LinearAgent"


def test_weak_signal_below_threshold_falls_back(router: QueryRouter) -> None:
    # "bug" alone is a weak, shared signal (weight 1) - not enough to route on.
    assert router.decide("bugs?").status is RouteStatus.FALLBACK


def test_decision_explains_itself(router: QueryRouter) -> None:
    decision = router.decide("Which PRs need my review?")
    assert decision.signals["GitHubAgent"] == ["pull request", "review"]
    assert decision.scores == {"GitHubAgent": 5.0, "LinearAgent": 0.0}
    assert decision.confidence == 1.0


def test_new_agent_plugs_in_without_router_changes() -> None:
    class WeatherAgent(BaseAgent):
        name = "WeatherAgent"
        label = "Weather"
        description = "Weather forecasts."
        keywords = {"weather": 3, "forecast": 3}

        @capability("forecast", "Today's forecast", default=True)
        def forecast(self, query: str) -> Reply:
            return "Sunny, 24°C.", []

    router = QueryRouter([*create_agents(), WeatherAgent()])
    result = router.handle("What's the weather today?")
    assert result.decision.agent == "WeatherAgent"
    assert result.message == "Sunny, 24°C."


def test_duplicate_agent_names_are_rejected() -> None:
    agents = create_agents()
    with pytest.raises(ValueError):
        QueryRouter([*agents, agents[0]])
