import pytest

from app.text import contains_phrase, normalize


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Show my open PRs!", "show my open pull request"),
        ("Pull-Requests", "pull request"),
        ("What's in the repos?", "what in the repository"),
        ("branches and issues", "branch and issue"),
        ("status of priorities", "status of priority"),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


def test_contains_phrase_matches_whole_words_only() -> None:
    assert contains_phrase("show my pull request", "pull request")
    assert not contains_phrase("reviewer list", "review")
    assert not contains_phrase("circuit breaker", "ci")
