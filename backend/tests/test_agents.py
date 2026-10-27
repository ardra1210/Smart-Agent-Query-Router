import pytest

from app.agents import BaseAgent, capability
from app.agents.base import Reply
from app.agents.github_agent import GitHubAgent
from app.agents.linear_agent import LinearAgent


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("show my open pull requests", "open_pull_requests"),
        ("anything waiting for my review?", "review_requests"),
        ("did CI pass on my branch?", "ci_runs"),
        ("list my recent commits", "recent_commits"),
        ("which repos do I have?", "repositories"),
        ("my github issues", "issues"),
        ("github", "open_pull_requests"),  # no capability keyword -> default
    ],
)
def test_github_capability_selection(query: str, expected: str) -> None:
    assert GitHubAgent().handle(query).capability == expected


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("what issues are assigned to me", "assigned_issues"),
        ("what is blocked", "blocked_issues"),
        ("any urgent tickets?", "priority_issues"),
        ("how is the current sprint going", "current_cycle"),
        ("what's in triage", "triage"),
        ("project status", "projects"),
    ],
)
def test_linear_capability_selection(query: str, expected: str) -> None:
    assert LinearAgent().handle(query).capability == expected


def test_responses_only_include_the_users_open_work() -> None:
    prs = GitHubAgent().handle("my open pull requests").items
    assert prs and all("by you" in pr.subtitle for pr in prs)

    issues = LinearAgent().handle("issues assigned to me").items
    assert issues and all(issue.status != "Done" for issue in issues)


def test_agent_must_declare_exactly_one_default_capability() -> None:
    with pytest.raises(TypeError):

        class NoDefault(BaseAgent):  # noqa: F841
            @capability("a", "A")
            def a(self, query: str) -> Reply:
                return "", []
