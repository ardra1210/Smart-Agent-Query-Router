"""Hard-coded fixtures standing in for real GitHub / Linear API responses."""

import json
from functools import cache
from pathlib import Path

_DIR = Path(__file__).parent


@cache
def load_fixture(name: str) -> dict:
    with open(_DIR / name, encoding="utf-8") as fh:
        return json.load(fh)
