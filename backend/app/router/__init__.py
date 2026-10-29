import os
from functools import cache

from app.agents import create_agents
from app.router.router import FALLBACK_MESSAGE, QueryRouter
from app.router.strategies import RoutingStrategy

STRATEGIES = ("keyword", "hybrid")


def build_router(mode: str | None = None) -> QueryRouter:
    """Wire a router with every registered agent.

    mode (default: $ROUTER_STRATEGY or "keyword"):
      keyword - deterministic keyword routing only; no network, no API key.
      hybrid  - keyword routing first, escalating to Claude when it is unsure.
    """
    mode = (mode or os.getenv("ROUTER_STRATEGY") or "keyword").lower()
    if mode not in STRATEGIES:
        raise ValueError(f"ROUTER_STRATEGY must be one of {STRATEGIES}, got {mode!r}")

    escalation: RoutingStrategy | None = None
    if mode == "hybrid":
        try:
            from app.router.strategies.llm import DEFAULT_MODEL, LLMStrategy
        except ImportError as exc:
            raise RuntimeError("hybrid routing needs: pip install -r requirements-llm.txt") from exc
        escalation = LLMStrategy(model=os.getenv("ROUTER_LLM_MODEL", DEFAULT_MODEL))
    return QueryRouter(create_agents(), escalation=escalation)


@cache
def get_router() -> QueryRouter:
    """The process-wide router."""
    return build_router()


__all__ = ["FALLBACK_MESSAGE", "QueryRouter", "build_router", "get_router"]
