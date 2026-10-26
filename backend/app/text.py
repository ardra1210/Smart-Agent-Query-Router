"""Text normalisation shared by routing strategies and agents.

Queries and keyword phrases both go through `normalize`, so a keyword such as
"pull request" matches "PRs", "pull-requests" or "Pull Requests".
"""

import re

_APOSTROPHES = re.compile(r"['’]")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

# Abbreviations expanded before stemming.
SYNONYMS: dict[str, str] = {
    "pr": "pull request",
    "prs": "pull request",
    "mr": "pull request",
    "mrs": "pull request",
    "repo": "repository",
    "repos": "repository",
    "gh": "github",
    "tix": "ticket",
}


def _stem(token: str) -> str:
    """Very small plural stripper: issues -> issue, branches -> branch."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith(("ches", "shes", "xes", "sses")):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def normalize(text: str) -> str:
    """Lowercase, drop punctuation, expand synonyms and strip plurals."""
    text = _APOSTROPHES.sub("", text.lower())
    tokens: list[str] = []
    for raw in _NON_ALNUM.sub(" ", text).split():
        expanded = SYNONYMS.get(raw, raw)
        tokens.extend(_stem(token) for token in expanded.split())
    return " ".join(tokens)


def contains_phrase(normalized_text: str, normalized_phrase: str) -> bool:
    """Whole-word phrase match on already-normalised strings."""
    return f" {normalized_phrase} " in f" {normalized_text} "


def plural(count: int, singular: str, plural_form: str | None = None) -> str:
    word = singular if count == 1 else (plural_form or f"{singular}s")
    return f"{count} {word}"
