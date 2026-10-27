from app.agents.base import BaseAgent, Reply, capability
from app.agents.mock_data import load_fixture
from app.agents.registry import register_agent
from app.models import ResponseItem
from app.text import plural

_OPEN_STATES = {"Todo", "In Progress", "Blocked"}


@register_agent
class LinearAgent(BaseAgent):
    name = "LinearAgent"
    label = "Linear"
    description = (
        "Answers questions about Linear: issues and tickets assigned to you, the "
        "current cycle or sprint, blocked or high-priority work, triage and projects."
    )
    keywords = {
        "linear": 5,
        "ticket": 3,
        "cycle": 3,
        "sprint": 3,
        "backlog": 3,
        "triage": 3,
        "story point": 3,
        "issue": 2,
        "assigned": 2,
        "blocked": 2,
        "blocker": 2,
        "priority": 2,
        "urgent": 2,
        "project": 2,
        "roadmap": 2,
        "estimate": 2,
        "epic": 2,
        "task": 2,
        "bug": 1,
        "milestone": 1,
    }

    def __init__(self) -> None:
        self._data = load_fixture("linear.json")

    def _my_open_issues(self) -> list[dict]:
        return [i for i in self._data["issues"] if i["assignee"] == "you" and i["state"] in _OPEN_STATES]

    # Capabilities are tried in declaration order; on equal keyword hits the
    # earlier (more specific) one wins, and `assigned_issues` is the default.

    @capability("blocked_issues", "Your issues that are blocked", keywords=("blocked", "blocker", "stuck"))
    def blocked_issues(self, query: str) -> Reply:
        blocked = [i for i in self._my_open_issues() if i["state"] == "Blocked"]
        items = [_issue_item(i, extra=f"blocked by {i.get('blocked_by', 'unknown')}") for i in blocked]
        return f"{plural(len(blocked), 'of your issues is', 'of your issues are')} blocked.", items

    @capability(
        "priority_issues",
        "Your urgent and high-priority issues",
        keywords=("urgent", "priority", "critical", "important"),
    )
    def priority_issues(self, query: str) -> Reply:
        hot = [i for i in self._my_open_issues() if i["priority"] in {"Urgent", "High"}]
        return f"You have {plural(len(hot), 'urgent or high-priority issue')}.", [_issue_item(i) for i in hot]

    @capability("current_cycle", "Progress of the current cycle", keywords=("cycle", "sprint", "iteration"))
    def current_cycle(self, query: str) -> Reply:
        cycle = self._data["current_cycle"]
        mine = [i for i in self._data["issues"] if i["assignee"] == "you" and i["in_cycle"]]
        message = (
            f"{cycle['name']} ({cycle['team']}, {cycle['starts']} → {cycle['ends']}): "
            f"{cycle['completed']}/{cycle['total']} issues done. "
            f"{plural(len(mine), 'issue')} in this cycle {'is' if len(mine) == 1 else 'are'} yours."
        )
        return message, [_issue_item(i) for i in mine]

    @capability("triage", "Unassigned issues in triage or backlog", keywords=("triage", "backlog", "unassigned"))
    def triage(self, query: str) -> Reply:
        waiting = [i for i in self._data["issues"] if i["assignee"] is None]
        return f"{plural(len(waiting), 'unassigned issue')} in triage or backlog.", [_issue_item(i) for i in waiting]

    @capability("projects", "Status of your team's projects", keywords=("project", "roadmap", "milestone"))
    def projects(self, query: str) -> Reply:
        projects = self._data["projects"]
        items = [
            ResponseItem(
                id=p["name"],
                title=p["name"],
                subtitle=f"{round(p['progress'] * 100)}% complete · target {p['target']}",
                status=p["status"],
            )
            for p in projects
        ]
        return f"{plural(len(projects), 'active project')}.", items

    @capability(
        "assigned_issues",
        "Open issues assigned to you",
        keywords=("assigned", "issue", "ticket", "task"),
        default=True,
    )
    def assigned_issues(self, query: str) -> Reply:
        mine = self._my_open_issues()
        return f"You have {plural(len(mine), 'open issue')} assigned to you.", [_issue_item(i) for i in mine]


def _issue_item(issue: dict, extra: str = "") -> ResponseItem:
    subtitle = f"{issue['priority']} priority · {issue['project']}"
    if extra:
        subtitle += f" · {extra}"
    return ResponseItem(id=issue["id"], title=issue["title"], subtitle=subtitle, status=issue["state"])
