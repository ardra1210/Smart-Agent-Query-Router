from fastapi import APIRouter, Depends

from app.models import AgentInfo, QueryRequest, QueryResult
from app.router import QueryRouter, get_router

api = APIRouter(prefix="/api")


@api.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@api.get("/agents", response_model=list[AgentInfo])
def list_agents(router: QueryRouter = Depends(get_router)) -> list[AgentInfo]:
    return [
        AgentInfo(
            name=agent.name,
            label=agent.label,
            description=agent.description,
            capabilities=agent.describe_capabilities(),
        )
        for agent in router.agents.values()
    ]


@api.post("/query", response_model=QueryResult)
def query(request: QueryRequest, router: QueryRouter = Depends(get_router)) -> QueryResult:
    return router.handle(request.query)
