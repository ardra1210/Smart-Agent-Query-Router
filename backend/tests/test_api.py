from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_list_agents() -> None:
    agents = client.get("/api/agents").json()
    assert {agent["name"] for agent in agents} == {"GitHubAgent", "LinearAgent"}
    assert all(agent["capabilities"] for agent in agents)


def test_query_returns_answer_and_routing_trace() -> None:
    body = client.post("/api/query", json={"query": "Show my open pull requests"}).json()
    assert body["decision"]["status"] == "routed"
    assert body["decision"]["agent"] == "GitHubAgent"
    assert body["response"]["items"]


def test_query_fallback() -> None:
    body = client.post("/api/query", json={"query": "What's the weather today?"}).json()
    assert body["message"] == "I cannot answer this question."


def test_empty_query_is_rejected() -> None:
    assert client.post("/api/query", json={"query": ""}).status_code == 422
