"""Command-line interface.

    python -m app.cli                              # interactive prompt
    python -m app.cli "Show my open pull requests" # one-shot
    python -m app.cli --trace "..."                # also print the routing decision
"""

import argparse

from app.logging_config import setup_logging
from app.models import QueryResult, RouteStatus
from app.router import get_router

_EXIT_WORDS = {"exit", "quit", ":q"}


def render(result: QueryResult, trace: bool) -> str:
    decision = result.decision
    lines: list[str] = []
    if decision.status is RouteStatus.ROUTED:
        lines.append(f"[{decision.agent}] {result.message}")
    else:
        lines.append(result.message)

    if result.response:
        for item in result.response.items:
            status = f" [{item.status}]" if item.status else ""
            lines.append(f"  • {item.id}  {item.title}{status}")
            if item.subtitle:
                lines.append(f"      {item.subtitle}")

    if trace and decision.status is not RouteStatus.MULTI:
        strategy = f"{decision.strategy} (escalated)" if decision.escalated else decision.strategy
        lines.append(
            f"  ↳ status={decision.status.value} agent={decision.agent} "
            f"confidence={decision.confidence:.2f} strategy={strategy} "
            f"latency={result.latency_ms}ms"
        )
        lines.append(f"    scores={decision.scores}")
        if decision.signals:
            lines.append(f"    signals={decision.signals}")
        if decision.reason:
            lines.append(f"    reason={decision.reason}")
        if result.response:
            lines.append(f"    capability={result.response.capability}")

    for part in result.parts:
        lines.append(f"\n  ── “{part.query}”")
        lines.append("  " + render(part, trace).replace("\n", "\n  "))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Route a question to the right agent.")
    parser.add_argument("query", nargs="*", help="question to ask (omit for interactive mode)")
    parser.add_argument("--trace", action="store_true", help="show the routing decision")
    parser.add_argument("--verbose", action="store_true", help="show router log lines")
    args = parser.parse_args()

    setup_logging("INFO" if args.verbose else "WARNING")
    router = get_router()

    if args.query:
        print(render(router.handle(" ".join(args.query)), args.trace))
        return

    labels = ", ".join(agent.label for agent in router.agents.values())
    mode = f"{router.strategy.name} + {router.escalation.name}" if router.escalation else router.strategy.name
    print(f"Smart Agent Query Router — agents: {labels}; routing: {mode}. Type 'exit' to quit.")
    while True:
        try:
            query = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not query:
            continue
        if query.lower() in _EXIT_WORDS:
            break
        print(render(router.handle(query), args.trace))


if __name__ == "__main__":
    main()
