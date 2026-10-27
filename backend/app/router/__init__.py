from functools import cache

from app.agents import create_agents
from app.router.router import FALLBACK_MESSAGE, QueryRouter


@cache
def get_router() -> QueryRouter:
    """The process-wide router, wired with every registered agent."""
    return QueryRouter(create_agents())


__all__ = ["FALLBACK_MESSAGE", "QueryRouter", "get_router"]
