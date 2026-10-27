from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.agents.base import BaseAgent


@dataclass
class StrategyResult:
    """Raw per-agent scores; the router turns these into a decision."""

    scores: dict[str, float]
    signals: dict[str, list[str]] = field(default_factory=dict)


class RoutingStrategy(ABC):
    name: str

    @abstractmethod
    def score(self, query: str, agents: Sequence[BaseAgent]) -> StrategyResult: ...
