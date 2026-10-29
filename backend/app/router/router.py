"""Routing policy: turn strategy scores into a decision and dispatch the query.

The decision rules, in order:
1. Blank query, or best score below `min_score`  -> fallback.
2. Runner-up within `ambiguity_ratio` of the best -> ask the user to clarify.
3. Otherwise                                      -> route to the best agent.

If the primary strategy ends in fallback or clarify and an `escalation`
strategy is configured (the optional LLM), the router asks it instead and
applies the same rules to its scores. Compound questions whose parts route
cleanly to different agents are answered part by part.
"""

import logging
import time
from collections.abc import Sequence

from app.agents.base import BaseAgent
from app.models import QueryResult, RouteStatus, RoutingDecision
from app.router.splitter import split_query
from app.router.strategies import KeywordStrategy, RoutingStrategy, StrategyError, StrategyResult

logger = logging.getLogger("router")

FALLBACK_MESSAGE = "I cannot answer this question."


class QueryRouter:
    def __init__(
        self,
        agents: Sequence[BaseAgent],
        strategy: RoutingStrategy | None = None,
        escalation: RoutingStrategy | None = None,
        min_score: float = 2.0,
        ambiguity_ratio: float = 0.75,
    ) -> None:
        names = [agent.name for agent in agents]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate agent names: {names}")
        self.agents = {agent.name: agent for agent in agents}
        self.strategy = strategy or KeywordStrategy()
        self.escalation = escalation
        self.min_score = min_score
        self.ambiguity_ratio = ambiguity_ratio

    # ------------------------------------------------------------------ decide

    def decide(self, query: str) -> RoutingDecision:
        """Route a single-intent question."""
        if not query.strip():
            return RoutingDecision(status=RouteStatus.FALLBACK, strategy=self.strategy.name)

        decision = self._decide_with(self.strategy, query)
        if decision.status is RouteStatus.ROUTED or self.escalation is None:
            return decision
        try:
            escalated = self._decide_with(self.escalation, query)
        except StrategyError as exc:
            logger.warning("escalation to %s failed (%s); keeping %s decision", self.escalation.name, exc, self.strategy.name)
            return decision
        escalated.escalated = True
        return escalated

    def _decide_with(self, strategy: RoutingStrategy, query: str) -> RoutingDecision:
        result = strategy.score(query, list(self.agents.values()))
        return self._apply_policy(result, strategy.name)

    def _apply_policy(self, result: StrategyResult, strategy_name: str) -> RoutingDecision:
        ranked = sorted(result.scores.items(), key=lambda kv: kv[1], reverse=True)
        top_name, top_score = ranked[0] if ranked else (None, 0.0)
        total = sum(score for _, score in ranked)

        decision = RoutingDecision(
            status=RouteStatus.FALLBACK,
            scores=result.scores,
            signals={name: hits for name, hits in result.signals.items() if hits},
            strategy=strategy_name,
            reason=result.reason,
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
        # Confidence = the chosen agent's share of all the evidence.
        decision.confidence = round(top_score / total, 2)
        return decision

    # ------------------------------------------------------------------ handle

    def handle(self, query: str) -> QueryResult:
        started = time.perf_counter()
        result = self._handle_compound(query) or self._answer(query, self.decide(query))
        result.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return result

    def _handle_compound(self, query: str) -> QueryResult | None:
        """Answer each part separately if the question spans several agents."""
        parts = split_query(query)
        if len(parts) < 2:
            return None
        # Only the fast primary strategy is used here, to avoid one LLM call per part.
        decisions = [self._decide_with(self.strategy, part) for part in parts]
        if any(d.status is not RouteStatus.ROUTED for d in decisions):
            return None
        agents = list(dict.fromkeys(d.agent for d in decisions))
        if len(agents) < 2:
            return None

        answers = [self._answer(part, decision) for part, decision in zip(parts, decisions)]
        labels = [self.agents[name].label for name in agents]
        decision = RoutingDecision(
            status=RouteStatus.MULTI,
            candidates=agents,
            confidence=min(d.confidence for d in decisions),
            strategy=self.strategy.name,
        )
        logger.info("route status=multi agents=%s query=%r", agents, query)
        return QueryResult(
            query=query,
            message=f"Your question has {len(parts)} parts, answered by {' and '.join(labels)}.",
            decision=decision,
            parts=answers,
            latency_ms=0.0,
        )

    def _answer(self, query: str, decision: RoutingDecision) -> QueryResult:
        started = time.perf_counter()
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

        logger.info(
            "route status=%s agent=%s confidence=%.2f strategy=%s%s scores=%s query=%r",
            decision.status.value,
            decision.agent,
            decision.confidence,
            decision.strategy,
            " (escalated)" if decision.escalated else "",
            decision.scores,
            query,
        )
        return QueryResult(
            query=query,
            message=message,
            decision=decision,
            response=response,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
