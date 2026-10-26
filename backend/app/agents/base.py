"""The contract every agent implements.

An agent declares *what* it covers (`keywords`, `description`) so that routing
strategies can score it, and implements *how* to answer through methods
decorated with `@capability`. The router never looks inside an agent beyond
that contract, and agents never know about the router or each other.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar

from app.models import AgentResponse, CapabilityInfo, ResponseItem
from app.text import contains_phrase, normalize

Reply = tuple[str, list[ResponseItem]]


@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    keywords: tuple[str, ...]
    handler: Callable[["BaseAgent", str], Reply]
    default: bool = False


def capability(
    name: str,
    description: str,
    keywords: tuple[str, ...] = (),
    default: bool = False,
) -> Callable:
    """Mark an agent method as a capability the agent can answer with."""

    def decorator(func: Callable[["BaseAgent", str], Reply]) -> Callable:
        func._capability = Capability(name, description, keywords, func, default)  # type: ignore[attr-defined]
        return func

    return decorator


class BaseAgent:
    name: ClassVar[str]
    label: ClassVar[str]
    description: ClassVar[str]
    # Routing signals: phrase -> weight. Avoid overlapping phrases
    # ("review" and "code review") so a single mention isn't counted twice.
    keywords: ClassVar[dict[str, float]] = {}
    capabilities: ClassVar[tuple[Capability, ...]] = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        found = tuple(
            attr._capability for attr in vars(cls).values() if hasattr(attr, "_capability")
        )
        if found:
            defaults = [cap for cap in found if cap.default]
            if len(defaults) != 1:
                raise TypeError(f"{cls.__name__} must mark exactly one capability as default")
            cls.capabilities = found

    def handle(self, query: str) -> AgentResponse:
        selected = self.select_capability(query)
        message, items = selected.handler(self, query)
        return AgentResponse(
            agent=self.name, capability=selected.name, message=message, items=items
        )

    def select_capability(self, query: str) -> Capability:
        """Pick the capability whose keywords best match; ties go to the first declared."""
        if not self.capabilities:
            raise NotImplementedError(f"{type(self).__name__} has no capabilities; override handle()")
        text = normalize(query)
        best = next(cap for cap in self.capabilities if cap.default)
        best_hits = 0
        for cap in self.capabilities:
            hits = sum(contains_phrase(text, normalize(keyword)) for keyword in cap.keywords)
            if hits > best_hits:
                best, best_hits = cap, hits
        return best

    def describe_capabilities(self) -> list[CapabilityInfo]:
        return [CapabilityInfo(name=c.name, description=c.description) for c in self.capabilities]
