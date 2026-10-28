import json

from app.agents import create_agents
from app.router import QueryRouter
from eval.run import DATASET, evaluate

# The dataset deliberately contains a few paraphrases the keyword strategy
# cannot handle; this floor guards against regressions, not perfection.
MIN_ACCURACY = 0.85


def test_routing_accuracy_does_not_regress() -> None:
    results = evaluate(QueryRouter(create_agents()), json.loads(DATASET.read_text()))
    accuracy = sum(expected == got for _, expected, got in results) / len(results)
    assert accuracy >= MIN_ACCURACY, f"routing accuracy dropped to {accuracy:.1%}"
