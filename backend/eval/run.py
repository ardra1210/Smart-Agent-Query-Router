"""Measure routing accuracy against a labelled dataset.

    python -m eval.run            # summary + misroutes
    python -m eval.run --all      # every query

Labels are an agent name, "fallback" or "clarify".
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from app.agents import create_agents
from app.models import RouteStatus
from app.router import QueryRouter

DATASET = Path(__file__).parent / "dataset.json"


def predict(router: QueryRouter, query: str) -> str:
    decision = router.decide(query)
    return decision.agent if decision.status is RouteStatus.ROUTED else decision.status.value


def evaluate(router: QueryRouter, cases: list[dict]) -> list[tuple[str, str, str]]:
    return [(case["query"], case["expected"], predict(router, case["query"])) for case in cases]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="print every case, not only misses")
    parser.add_argument("--min-accuracy", type=float, default=0.0, help="exit 1 below this accuracy")
    args = parser.parse_args()

    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    results = evaluate(QueryRouter(create_agents()), cases)
    correct = sum(expected == got for _, expected, got in results)
    accuracy = correct / len(results)

    totals, hits = Counter(), Counter()
    for _, expected, got in results:
        totals[expected] += 1
        hits[expected] += expected == got

    print(f"Accuracy: {correct}/{len(results)} = {accuracy:.1%}\n")
    print(f"{'label':<14}{'correct':>10}")
    for label in sorted(totals):
        print(f"{label:<14}{hits[label]:>6}/{totals[label]}")

    shown = results if args.all else [r for r in results if r[1] != r[2]]
    if shown:
        print(f"\n{'query':<48}{'expected':<14}got")
        for query, expected, got in shown:
            mark = "  " if expected == got else "✗ "
            print(f"{mark}{query[:46]:<46}{expected:<14}{got}")

    sys.exit(1 if accuracy < args.min_accuracy else 0)


if __name__ == "__main__":
    main()
