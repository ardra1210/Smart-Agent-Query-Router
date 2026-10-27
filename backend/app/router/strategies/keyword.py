from collections.abc import Sequence

from app.agents.base import BaseAgent
from app.router.strategies.base import RoutingStrategy, StrategyResult
from app.text import contains_phrase, normalize


class KeywordStrategy(RoutingStrategy):
    """Scores each agent by summing the weights of its keywords found in the query.

    Deterministic, instant and free, which makes it easy to test and explain.
    """

    name = "keyword"

    def score(self, query: str, agents: Sequence[BaseAgent]) -> StrategyResult:
        text = normalize(query)
        scores: dict[str, float] = {}
        signals: dict[str, list[str]] = {}
        for agent in agents:
            matched = [kw for kw in agent.keywords if contains_phrase(text, normalize(kw))]
            scores[agent.name] = float(sum(agent.keywords[kw] for kw in matched))
            signals[agent.name] = matched
        return StrategyResult(scores=scores, signals=signals)
