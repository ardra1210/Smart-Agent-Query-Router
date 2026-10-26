"""Data shapes shared by the router, the agents, the CLI and the API."""

from enum import Enum

from pydantic import BaseModel, Field


class ResponseItem(BaseModel):
    """One row in an agent answer (a pull request, an issue, a commit...)."""

    id: str
    title: str
    subtitle: str = ""
    status: str | None = None


class AgentResponse(BaseModel):
    agent: str
    capability: str
    message: str
    items: list[ResponseItem] = Field(default_factory=list)


class RouteStatus(str, Enum):
    ROUTED = "routed"
    CLARIFY = "clarify"
    FALLBACK = "fallback"


class RoutingDecision(BaseModel):
    """Why the router picked (or refused to pick) an agent."""

    status: RouteStatus
    agent: str | None = None
    confidence: float = 0.0
    scores: dict[str, float] = Field(default_factory=dict)
    signals: dict[str, list[str]] = Field(default_factory=dict)
    candidates: list[str] = Field(default_factory=list)
    strategy: str


class QueryResult(BaseModel):
    query: str
    message: str
    decision: RoutingDecision
    response: AgentResponse | None = None
    latency_ms: float


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class CapabilityInfo(BaseModel):
    name: str
    description: str


class AgentInfo(BaseModel):
    name: str
    label: str
    description: str
    capabilities: list[CapabilityInfo]
