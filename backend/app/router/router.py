"""Routing policy: turn strategy scores into a decision and dispatch the query.

The decision rules, in order:
1. Blank query, or best score below `min_score`  -> fallback.
2. Runner-up within `ambiguity_ratio` of the best -> ask the user to clarify.
3. Otherwise                                      -> route to the best agent.
"""

import logging
import time
from collections.abc import Sequence

from app.agents.base import BaseAgent
from app.models import QueryResult, RouteStatus, RoutingDecision
from app.router.strategies import KeywordStrategy, RoutingStrategy

logger = logging.getLogger("router")

FALLBACK_MESSAGE = "I cannot answer this question."


class QueryRouter:
    def __init__(
        self,
        agents: Sequence[BaseAgent],
        strategy: RoutingStrategy | None = None,
        min_score: float = 2.0,
        ambiguity_ratio: float = 0.75,
    ) -> None:
        names = [agent.name for agent in agents]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate agent names: {names}")
        self.agents = {agent.name: agent for agent in agents}
        self.strategy = strategy or KeywordStrategy()
        self.min_score = min_score
        self.ambiguity_ratio = ambiguity_ratio

    def decide(self, query: str) -> RoutingDecision:
        if not query.strip():
            return RoutingDecision(status=RouteStatus.FALLBACK, strategy=self.strategy.name)

        result = self.strategy.score(query, list(self.agents.values()))
        ranked = sorted(result.scores.items(), key=lambda kv: kv[1], reverse=True)
        top_name, top_score = ranked[0] if ranked else (None, 0.0)
        total = sum(score for _, score in ranked)

        decision = RoutingDecision(
            status=RouteStatus.FALLBACK,
            scores=result.scores,
            signals={name: hits for name, hits in result.signals.items() if hits},
            strategy=self.strategy.name,
        )
        if top_score < self.min_score:
            return decision

        contenders = [name for name, score in ranked if score >= top_score * self.ambiguity_ratio]
        if len(contenders) > 1:
            decision.status = RouteStatus.CLARIFY
            decision.candidates = contenders
            return decision

        decision.status = RouteStatus.ROUTED
        decision.agent = top_name
        # Confidence = the chosen agent's share of all keyword evidence.
        decision.confidence = round(top_score / total, 2)
        return decision

    def handle(self, query: str) -> QueryResult:
        started = time.perf_counter()
        decision = self.decide(query)
        response = None

        if decision.status is RouteStatus.ROUTED:
            response = self.agents[decision.agent].handle(query)
            message = response.message
        elif decision.status is RouteStatus.CLARIFY:
            labels = [self.agents[name].label for name in decision.candidates]
            message = (
                f"Your question could be about {' or '.join(labels)}. "
                f"Please mention which one you mean, e.g. include \"{labels[0]}\" in your question."
            )
        else:
            message = FALLBACK_MESSAGE

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "route status=%s agent=%s confidence=%.2f scores=%s query=%r",
            decision.status.value,
            decision.agent,
            decision.confidence,
            decision.scores,
            query,
        )
        return QueryResult(
            query=query, message=message, decision=decision, response=response, latency_ms=latency_ms
        )
