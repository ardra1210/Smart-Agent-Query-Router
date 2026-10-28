"""LLM routing strategy backed by Claude.

Used only as an escalation path: the router calls it when keyword routing is
unsure (no match, weak match or a tie). The model's verdict is translated into
the same score shape as the keyword strategy, so one decision policy applies.

Requires `pip install -r requirements-llm.txt` and Anthropic credentials
(ANTHROPIC_API_KEY or an `ant auth login` profile).
"""

import json
import logging
from collections.abc import Sequence

import anthropic

from app.agents.base import BaseAgent
from app.router.strategies.base import RoutingStrategy, StrategyError, StrategyResult

logger = logging.getLogger("router.llm")

DEFAULT_MODEL = "claude-opus-5-5"
NONE = "none"
AMBIGUOUS = "ambiguous"
# Score given to the agent(s) the model picks; comfortably above the router's min_score.
VERDICT_SCORE = 10.0

_INSTRUCTIONS = """You route questions from a software engineer to the agent that can answer them.

Agents:
{agents}

Pick the single agent whose data can answer the question.
- Use "{none}" when no agent can answer it (weather, trivia, small talk, anything outside these tools).
- Use "{ambiguous}" only when the question fits more than one agent equally and gives no hint which
  one is meant; list those agents in "candidates". Otherwise leave "candidates" empty.
- "reason" is one short sentence explaining the choice."""


class LLMStrategy(RoutingStrategy):
    name = "llm"

    def __init__(self, model: str = DEFAULT_MODEL, client: anthropic.Anthropic | None = None) -> None:
        self.model = model
        self._client = client or anthropic.Anthropic(timeout=20.0, max_retries=1)

    def score(self, query: str, agents: Sequence[BaseAgent]) -> StrategyResult:
        names = [agent.name for agent in agents]
        try:
            response = self._client.beta.messages.create(
                model=self.model,
                max_tokens=2048,
                system=_system_prompt(agents),
                messages=[{"role": "user", "content": query}],
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": _schema(names)}},
                # On a policy decline, let the API retry on its recommended fallback model.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as exc:
            raise StrategyError("authentication failed; check ANTHROPIC_API_KEY") from exc
        except anthropic.RateLimitError as exc:
            raise StrategyError("rate limited by the Claude API") from exc
        except anthropic.APIStatusError as exc:
            raise StrategyError(f"Claude API error {exc.status_code}") from exc
        except anthropic.APIConnectionError as exc:
            raise StrategyError("could not reach the Claude API") from exc
        except anthropic.CredentialsError as exc:
            raise StrategyError(f"credentials problem: {exc}") from exc
        except TypeError as exc:
            # The SDK raises TypeError at request time when no credentials resolve.
            if "authentication" not in str(exc).lower():
                raise
            raise StrategyError("no Anthropic credentials configured") from exc

        if response.stop_reason != "end_turn":
            raise StrategyError(f"model stopped early ({response.stop_reason})")
        text = next((block.text for block in response.content if block.type == "text"), None)
        if text is None:
            raise StrategyError("model returned no text")
        return verdict_to_result(json.loads(text), names)


def verdict_to_result(verdict: dict, names: list[str]) -> StrategyResult:
    """Translate {"agent", "candidates", "reason"} into router scores."""
    scores = {name: 0.0 for name in names}
    agent = verdict.get("agent")
    if agent == AMBIGUOUS:
        for name in verdict.get("candidates", []):
            if name in scores:
                scores[name] = VERDICT_SCORE
    elif agent in scores:
        scores[agent] = VERDICT_SCORE
    elif agent != NONE:
        raise StrategyError(f"model chose an unknown agent: {agent!r}")
    return StrategyResult(scores=scores, reason=verdict.get("reason"))


def _system_prompt(agents: Sequence[BaseAgent]) -> str:
    lines = []
    for agent in agents:
        abilities = "; ".join(cap.description for cap in agent.capabilities)
        lines.append(f"- {agent.name}: {agent.description} Can answer: {abilities}.")
    return _INSTRUCTIONS.format(agents="\n".join(lines), none=NONE, ambiguous=AMBIGUOUS)


def _schema(names: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "agent": {"type": "string", "enum": [*names, NONE, AMBIGUOUS]},
            "candidates": {"type": "array", "items": {"type": "string", "enum": names}},
            "reason": {"type": "string"},
        },
        "required": ["agent", "candidates", "reason"],
        "additionalProperties": False,
    }
