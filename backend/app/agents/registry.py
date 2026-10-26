"""Agent registry with auto-discovery.

Any module in `app/agents/` that defines a class decorated with
`@register_agent` is picked up automatically, so adding an agent never
requires touching the router or this file.
"""

import importlib
import pkgutil

from app.agents.base import BaseAgent

_REGISTRY: dict[str, type[BaseAgent]] = {}
_INFRASTRUCTURE_MODULES = {"base", "registry"}


def register_agent(cls: type[BaseAgent]) -> type[BaseAgent]:
    for attr in ("name", "label", "description"):
        if not getattr(cls, attr, None):
            raise TypeError(f"{cls.__name__} must define a non-empty `{attr}`")
    existing = _REGISTRY.get(cls.name)
    if existing is not None and existing is not cls:
        raise ValueError(f"An agent named {cls.name!r} is already registered")
    _REGISTRY[cls.name] = cls
    return cls


def discover_agents() -> None:
    """Import every agent module in this package so their decorators run."""
    import app.agents as package

    for module in pkgutil.iter_modules(package.__path__):
        if module.ispkg or module.name in _INFRASTRUCTURE_MODULES:
            continue
        importlib.import_module(f"{package.__name__}.{module.name}")


def create_agents() -> list[BaseAgent]:
    discover_agents()
    return [cls() for cls in _REGISTRY.values()]
