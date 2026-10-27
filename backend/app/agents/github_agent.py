from app.agents.base import BaseAgent, Reply, capability
from app.agents.mock_data import load_fixture
from app.agents.registry import register_agent
from app.models import ResponseItem
from app.text import plural


@register_agent
class GitHubAgent(BaseAgent):
    name = "GitHubAgent"
    label = "GitHub"
    description = (
        "Answers questions about GitHub: pull requests, code reviews, commits, "
        "repositories, GitHub issues and CI workflow runs."
    )
    keywords = {
        "github": 5,
        "pull request": 3,
        "repository": 3,
        "commit": 3,
        "branch": 3,
        "fork": 3,
        "gist": 3,
        "merge": 2,
        "review": 2,
        "reviewer": 2,
        "workflow": 2,
        "ci": 2,
        "pipeline": 2,
        "build": 2,
        "release": 2,
        "issue": 2,
        "bug": 1,
        "milestone": 1,
    }

    def __init__(self) -> None:
        self._data = load_fixture("github.json")

    # Capabilities are tried in declaration order; on equal keyword hits the
    # earlier (more specific) one wins, and `open_pull_requests` is the default.

    @capability(
        "review_requests",
        "Pull requests waiting for your review",
        keywords=("review", "reviewer", "approve", "approval"),
    )
    def review_requests(self, query: str) -> Reply:
        prs = [pr for pr in self._data["pull_requests"] if pr["review_requested"] and pr["state"] == "open"]
        return f"{plural(len(prs), 'pull request')} waiting for your review.", [_pr_item(pr) for pr in prs]

    @capability(
        "ci_runs",
        "Recent CI workflow runs",
        keywords=("ci", "workflow", "build", "pipeline", "check", "action", "failing"),
    )
    def ci_runs(self, query: str) -> Reply:
        runs = self._data["workflow_runs"]
        failing = sum(run["status"] == "failure" for run in runs)
        items = [
            ResponseItem(
                id=f"#{run['id']}",
                title=f"{run['workflow']} on {run['branch']}",
                subtitle=f"{run['repo']} · started {run['started']}",
                status=run["status"],
            )
            for run in runs
        ]
        return f"{plural(len(runs), 'recent workflow run')}, {failing} failing.", items

    @capability("issues", "GitHub issues assigned to you", keywords=("issue", "bug"))
    def issues(self, query: str) -> Reply:
        mine = [issue for issue in self._data["issues"] if issue["assigned_to_me"]]
        items = [
            ResponseItem(
                id=f"{issue['repo']}#{issue['number']}",
                title=issue["title"],
                subtitle=", ".join(issue["labels"]),
                status="open",
            )
            for issue in mine
        ]
        return f"You have {plural(len(mine), 'open GitHub issue')} assigned to you.", items

    @capability("recent_commits", "Your most recent commits", keywords=("commit", "pushed", "push", "history"))
    def recent_commits(self, query: str) -> Reply:
        commits = self._data["commits"]
        items = [
            ResponseItem(
                id=commit["sha"],
                title=commit["message"],
                subtitle=f"{commit['repo']} · {commit['branch']} · {commit['date']}",
            )
            for commit in commits
        ]
        return f"Your last {plural(len(commits), 'commit')}:", items

    @capability("repositories", "Repositories you have access to", keywords=("repository",))
    def repositories(self, query: str) -> Reply:
        repos = self._data["repositories"]
        items = [
            ResponseItem(
                id=repo["name"],
                title=repo["name"],
                subtitle=f"{repo['language']} · {plural(repo['open_issues'], 'open issue')}",
                status=repo["visibility"],
            )
            for repo in repos
        ]
        return f"You have access to {plural(len(repos), 'repository', 'repositories')}.", items

    @capability(
        "open_pull_requests",
        "Your open pull requests",
        keywords=("pull request", "open"),
        default=True,
    )
    def open_pull_requests(self, query: str) -> Reply:
        prs = [pr for pr in self._data["pull_requests"] if pr["author"] == "you" and pr["state"] == "open"]
        return f"You have {plural(len(prs), 'open pull request')}.", [_pr_item(pr) for pr in prs]


def _pr_item(pr: dict) -> ResponseItem:
    return ResponseItem(
        id=f"{pr['repo']}#{pr['number']}",
        title=pr["title"],
        subtitle=f"by {pr['author']} · updated {pr['updated']}",
        status=f"checks {pr['checks']}",
    )
