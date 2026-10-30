# Smart Agent Query Router

Routes a natural-language question to the agent that can answer it — a mock
**GitHubAgent** or a mock **LinearAgent** — declines anything out of scope with
`I cannot answer this question.`, and explains every routing decision.

Available as a **web UI** (React + TypeScript + Tailwind), a **REST API** (FastAPI) and
a **CLI**, and runs with a single `docker compose up`.

![Web UI: a routed answer with the "Why this answer?" panel open](docs/screenshots/ui-routed-trace.png)

## Index

1. [Requirements and what's done](#1-requirements-and-whats-done)
   - [Requirement checklist](#requirement-checklist)
   - [Run it locally](#run-it-locally)
   - [API docs (`/docs`) in action](#api-docs-docs-in-action)
   - [CLI](#cli)
   - [Tests and routing evaluation](#tests-and-routing-evaluation)
2. [Docker](#2-docker)
   - [Start the stack](#start-the-stack)
   - [Calling the API through Docker](#calling-the-api-through-docker)
   - [Routing logs](#routing-logs)
   - [Docker commands](#docker-commands)
3. [Extra features](#3-extra-features)
   - [Feature list](#feature-list)
   - [How routing works](#how-routing-works)
   - [Hybrid routing with Claude (optional)](#hybrid-routing-with-claude-optional)
   - [Multi-part questions](#multi-part-questions)
   - [Adding an agent](#adding-an-agent)
   - [Design decisions](#design-decisions)
   - [Project layout](#project-layout)
   - [Continuous integration](#continuous-integration)
   - [Assumptions](#assumptions)
   - [Limitations and next steps](#limitations-and-next-steps)
4. [Frontend](#4-frontend)
   - [Run the frontend](#run-the-frontend)
   - [Screens](#screens)
5. [Command reference](#5-command-reference)

---

## 1. Requirements and what's done

### Requirement checklist

| Requirement | Status | Where |
|---|---|---|
| Route a question by intent to **GitHubAgent** or **LinearAgent** | ✅ Done | [router.py](backend/app/router/router.py), [keyword.py](backend/app/router/strategies/keyword.py) |
| "Show my open pull requests" → GitHubAgent | ✅ Done | [screenshot](#api-docs-docs-in-action), [test_router.py](backend/tests/test_router.py) |
| "What issues are assigned to me?" → LinearAgent | ✅ Done | [screenshot](#calling-the-api-through-docker), [test_router.py](backend/tests/test_router.py) |
| Out-of-scope questions return exactly `I cannot answer this question.` | ✅ Done | [screenshot](#api-docs-docs-in-action), `FALLBACK_MESSAGE` in [router.py](backend/app/router/router.py) |
| CLI **or** minimal API | ✅ Both, plus a web UI | [cli.py](backend/app/cli.py), [routes.py](backend/app/api/routes.py), [frontend/](frontend/) |
| Clear separation of routing logic and agent logic | ✅ Done | [app/router/](backend/app/router/) never touches agent internals; [app/agents/](backend/app/agents/) never imports the router |
| Mock agents | ✅ Done | [github_agent.py](backend/app/agents/github_agent.py), [linear_agent.py](backend/app/agents/linear_agent.py), JSON fixtures in [mock_data/](backend/app/agents/mock_data/) |
| *Nice to have:* unit tests | ✅ 57 tests | [backend/tests/](backend/tests/) |
| *Nice to have:* logging of routing decisions | ✅ Every decision logged | [screenshot](#routing-logs) |
| *Nice to have:* extensible agent design | ✅ One file per agent, auto-discovered | [Adding an agent](#adding-an-agent) |
| README with setup and assumptions | ✅ This file | [Assumptions](#assumptions) |

The three example questions, end to end:

| Question | Result |
|---|---|
| Show my open pull requests | `[GitHubAgent] You have 3 open pull requests.` |
| What issues are assigned to me? | `[LinearAgent] You have 4 open issues assigned to you.` |
| What's the weather today? | `I cannot answer this question.` |

### Run it locally

Requires Python 3.11+ (tested on 3.13). Node.js 20+ is needed only for the web UI.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

uvicorn app.main:app --reload          # API on http://localhost:8000
                                       # interactive docs on http://localhost:8000/docs
```

Prefer containers? Skip to [Docker](#2-docker).

### API docs (`/docs`) in action

FastAPI generates interactive Swagger docs at **http://localhost:8000/docs**.

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/query` | `{"query": "..."}` → answer + routing decision |
| `GET` | `/api/agents` | Registered agents and their capabilities |
| `GET` | `/api/health` | Liveness check and the active routing mode |

![Swagger UI listing the three endpoints and the schemas](docs/screenshots/api-docs.png)

**Routed:** `POST /api/query` with *"Which PRs need my review?"* goes to GitHubAgent
with confidence 1.0. The response shows the scores, the matched keywords (`pull request`,
`review`) and the capability that answered (`review_requests`).

![Swagger "Try it out": a routed query](docs/screenshots/api-query-routed.png)

**Out of scope:** *"What's the weather today?"* scores 0 for both agents, so the router
declines with the exact required message.

![Swagger "Try it out": an out-of-scope query](docs/screenshots/api-query-fallback.png)

**Health:** `GET /api/health` reports the active routing mode.

![Swagger "Try it out": the health endpoint](docs/screenshots/api-health.png)

`decision.status` is one of:

| Status | Meaning |
|---|---|
| `routed` | One agent answered (`decision.agent`, `response`) |
| `clarify` | The question fits more than one agent; `decision.candidates` lists them |
| `fallback` | Out of scope: `message` is `I cannot answer this question.` |
| `multi` | A compound question; each sub-answer is in `parts` |

### CLI

```bash
cd backend
python -m app.cli                                        # interactive prompt
python -m app.cli "Show my open pull requests"           # one-shot
python -m app.cli --trace "Which PRs need my review?"    # include the routing trace
python -m app.cli --verbose "..."                        # also print the router's log lines
```

![CLI with --trace for a routed and an ambiguous question](docs/screenshots/cli-trace.png)

### Tests and routing evaluation

```bash
cd backend
pytest -v                 # 57 unit and API tests
python -m eval.run        # routing accuracy on a labelled dataset
```

`pytest` covers text normalisation, capability selection, the routing policy
(threshold, ambiguity, fallback), compound questions, LLM escalation (with a stub),
the LLM request/response handling (with a fake client, no network), the API, and a
floor on eval accuracy.

![pytest -v: 57 passed](docs/screenshots/tests-pytest.png)

`eval.run` scores the router against [eval/dataset.json](backend/eval/dataset.json):
49 labelled questions covering GitHub, Linear, out-of-scope, ambiguous, compound and
deliberately hard cases.

![Routing evaluation: 44/49 = 89.8%](docs/screenshots/tests-eval.png)

The five misses are intentional hard cases, kept so the score is honest:

- Four are paraphrases with no domain keywords ("What am I supposed to be working
  on?"). They **fail safe**: the router declines rather than guessing wrong. These are
  exactly the questions [hybrid mode](#hybrid-routing-with-claude-optional) sends to
  Claude.
- One is a false positive ("Build me a sandwich" → GitHub, because of "build").

A test ([test_eval.py](backend/tests/test_eval.py)) fails if accuracy ever drops below
85%, so a keyword change that breaks routing is caught.

---

## 2. Docker

The whole app (API + web UI) runs from one command. Only Docker is required.

| Service | Image | Port | Notes |
|---|---|---|---|
| `backend` | `python:3.13-slim` + uvicorn | `8000` | Health check on `/api/health` |
| `frontend` | Node 22 build → `nginx:1.27-alpine` | `3000` | Serves the built UI and proxies `/api` to the backend |

The frontend starts only after the backend reports healthy.

### Start the stack

```bash
docker compose up --build -d     # build and start in the background
docker compose ps                # check status
```

- Web UI: http://localhost:3000
- API docs: http://localhost:8000/docs

![docker compose up and ps: backend healthy, frontend started](docs/screenshots/docker-up.png)

### Calling the API through Docker

Requests to `:3000/api/...` go through nginx to the backend container:

```bash
curl -s localhost:3000/api/health

curl -s -X POST localhost:3000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Show my open pull requests"}' | jq
```

![curl through nginx to the backend](docs/screenshots/docker-curl.png)

### Routing logs

Every routing decision is logged by the `router` logger with its status, agent,
confidence, strategy and scores. Here it is for routed, fallback, clarify and multi-part
questions:

```bash
docker compose logs -f backend
```

![Backend container logs showing each routing decision](docs/screenshots/docker-logs.png)

### Docker commands

| Task | Command |
|---|---|
| Build and start | `docker compose up --build -d` |
| Status | `docker compose ps` |
| Follow backend logs | `docker compose logs -f backend` |
| Follow all logs | `docker compose logs -f` |
| Stop and remove | `docker compose down` |
| Rebuild one service | `docker compose up --build -d backend` |
| Shell into the backend | `docker compose exec backend sh` |

**Configuration.** Copy [.env.example](.env.example) to `.env` to change ports or the
routing mode:

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
|---|---|---|
| `ROUTER_STRATEGY` | `keyword` | `keyword`, or `hybrid` to escalate unsure questions to Claude |
| `ANTHROPIC_API_KEY` | *(empty)* | Needed only for `hybrid` |
| `ROUTER_LLM_MODEL` | `claude-opus-5-5` | Model used in `hybrid` mode |
| `LOG_LEVEL` | `INFO` | Backend log level |
| `BACKEND_PORT` | `8000` | Host port for the API |
| `FRONTEND_PORT` | `3000` | Host port for the web UI |

---

## 3. Extra features

### Feature list

Beyond the requirements:

| # | Feature | What it does |
|---|---|---|
| 1 | **Clarification instead of guessing** | "Show my issues" fits both GitHub and Linear, so the router asks which one. The UI shows one button per tool. |
| 2 | **Explainable decisions** | Every answer returns each agent's score, the matched keywords and a confidence value ("Why this answer?" in the UI, `--trace` in the CLI). |
| 3 | **Text normalisation** | Shorthand is expanded (`PRs` → `pull request`, `repo` → `repository`, `gh` → `github`) and plurals are stripped. |
| 4 | **Multi-part questions** | "Show my open PRs and my blocked Linear tickets" gets one answer from each agent. |
| 5 | **Optional LLM escalation** | In `hybrid` mode, questions the keyword router can't settle go to Claude. It falls back safely if Claude is unavailable. |
| 6 | **Two-level routing** | The router picks the agent, and the agent picks a capability (review requests, CI runs, current cycle, blocked issues, …). |
| 7 | **Plug-in agents** | A new agent is one file. It's auto-discovered and appears in the API, the UI and the LLM's choices. |
| 8 | **Pluggable scoring** | Keyword and LLM scoring share one interface and one decision policy. |
| 9 | **Measured accuracy** | A labelled dataset and an accuracy report, with a regression floor enforced by a test. |
| 10 | **Three interfaces** | Web UI, REST API with Swagger docs, and a CLI with an interactive mode. |
| 11 | **Docker and CI** | One-command startup with health checks; GitHub Actions runs tests, eval, lint and build. |

### How routing works

```text
            ┌──────────────┐   scores    ┌──────────────┐  routed   ┌─────────────┐
 query ───► │   Keyword    │ ──────────► │ QueryRouter  │ ────────► │   Agent     │ ──► answer
            │  strategy    │             │  (policy)    │           │ .handle()   │
            └──────────────┘             └──────┬───────┘           └─────────────┘
                                                │ unsure?
                                                ▼
                                      ┌──────────────────┐
                                      │ LLM strategy     │  (optional, ROUTER_STRATEGY=hybrid)
                                      │ same policy      │
                                      └────────┬─────────┘
                                               ▼
                         route / "Did you mean GitHub or Linear?" / "I cannot answer this question."
```

1. **Normalise** ([text.py](backend/app/text.py)): lowercase, drop punctuation, expand
   abbreviations, strip plurals.
2. **Score** ([keyword.py](backend/app/router/strategies/keyword.py)): each agent
   declares weighted keywords (`"github": 5`, `"pull request": 3`, `"issue": 2`, …).
   An agent's score is the sum of the weights found in the question, matched on whole
   words.
3. **Decide** ([router.py](backend/app/router/router.py)):
   - best score below `min_score` (2.0) → **fallback**: `I cannot answer this question.`
   - runner-up at least 75% of the best → **clarify** instead of guessing
   - otherwise → **route** to the best agent. Confidence is its share of all the evidence.
4. **Escalate (optional):** if step 3 ends in fallback or clarify and hybrid mode is on,
   the question goes to Claude. Its verdict goes through the same rules.
5. **Answer:** the agent picks one of its *capabilities* and returns a message plus
   structured items.

Worked example, *"What issues are assigned to me?"*:

| Agent | Matched keywords | Score |
|---|---|---|
| GitHubAgent | `issue` (2) | 2.0 |
| LinearAgent | `issue` (2), `assigned` (2) | 4.0 |

The runner-up (2.0) is 50% of the best (4.0), below the 75% ambiguity ratio, so it
routes to **LinearAgent** with confidence 4 / (4 + 2) = 0.67. Without "assigned", both
score 2.0 and the router asks which tool you mean.

### Hybrid routing with Claude (optional)

```bash
cd backend
pip install -r requirements-llm.txt
export ANTHROPIC_API_KEY=...
export ROUTER_STRATEGY=hybrid
uvicorn app.main:app --reload
python -m eval.run --strategy hybrid    # compare against the keyword baseline
```

- Claude is called **only** when keyword routing ends in fallback or clarify. Confident
  answers stay instant, free and deterministic.
- The model must reply with JSON that matches a schema. The agent field is an enum of
  the registered agents plus `none` and `ambiguous`, so it can't invent an agent.
- Claude's one-line reason is returned in `decision.reason` and shown in the UI.
- If the call fails (no credentials, network error, rate limit, refusal), the router logs
  a warning and keeps the keyword decision. The app never breaks because the LLM is
  unavailable.
- The model is configurable with `ROUTER_LLM_MODEL`.

Hybrid mode is covered by tests with a stub strategy and a fake client. Its accuracy
against the live API is measured with `python -m eval.run --strategy hybrid`.

### Multi-part questions

[splitter.py](backend/app/router/splitter.py) splits a question on connectors such as
"and", "also", "plus" and ";". The split is used only if **every** part routes cleanly
and the parts reach **more than one** agent:

| Question | Result |
|---|---|
| Show my open PRs and my blocked Linear tickets | `multi`: GitHub part + Linear part |
| What bugs and issues do I have | kept as one question, which asks for clarification (the halves don't route on their own) |
| Show my PRs and my commits | one GitHub answer (both parts go to the same agent) |

### Adding an agent

Create one file in `backend/app/agents/`. Nothing else changes:

```python
from app.agents.base import BaseAgent, Reply, capability
from app.agents.registry import register_agent


@register_agent
class SlackAgent(BaseAgent):
    name = "SlackAgent"
    label = "Slack"
    description = "Answers questions about Slack messages and channels."
    keywords = {"slack": 5, "channel": 3, "dm": 3, "mention": 2}

    @capability("mentions", "Messages that mention you", keywords=("mention",), default=True)
    def mentions(self, query: str) -> Reply:
        return "You have 2 unread mentions.", []
```

The registry discovers it on startup. It then appears in `/api/agents`, in the UI
sidebar, in keyword routing and in the LLM's list of choices.

### Design decisions

- **Routing and agent logic are separate.** Agents expose a small contract (`name`,
  `label`, `description`, `keywords`, `handle(query)`). The router only scores and
  dispatches. Agents never see the router or each other.
- **Deterministic first, LLM second.** Keyword routing is instant, free, testable and
  explainable, and handles most questions. The LLM is used only where keywords fail.
- **Ask, don't guess.** Equal evidence for two agents triggers a clarification.
- **Fail closed.** Weak evidence returns `I cannot answer this question.` rather than a
  best guess. An unavailable LLM falls back to keyword routing.
- **One decision policy.** Strategies only return scores. Threshold, ambiguity,
  escalation and multi-part logic all live in `QueryRouter`.
- **Two-level routing.** The router picks the agent and the agent picks a capability, so
  agents can grow without touching the router.

### Project layout

```text
backend/
├── app/
│   ├── agents/              # agent logic: knows nothing about routing
│   │   ├── base.py          # BaseAgent contract + @capability decorator
│   │   ├── registry.py      # @register_agent + auto-discovery
│   │   ├── github_agent.py
│   │   ├── linear_agent.py
│   │   └── mock_data/       # JSON fixtures standing in for real APIs
│   ├── router/              # routing logic: knows nothing about agent internals
│   │   ├── router.py        # QueryRouter: decision policy, escalation, dispatch
│   │   ├── splitter.py      # compound-question splitting
│   │   └── strategies/      # keyword (default) and llm (optional) scoring
│   ├── api/routes.py        # FastAPI endpoints
│   ├── cli.py               # command-line interface
│   ├── models.py            # shared Pydantic models
│   └── text.py              # normalisation helpers
├── eval/                    # labelled dataset + accuracy report
├── tests/
└── Dockerfile
frontend/
├── src/
│   ├── App.tsx              # chat state, layout, example questions
│   ├── api.ts               # typed API client
│   ├── types.ts             # mirrors backend models
│   └── components/          # AssistantMessage, RoutingTrace, Sidebar, Composer, StatusBadge
├── nginx.conf               # serves the UI, proxies /api in Docker
└── Dockerfile
docker-compose.yml
.github/workflows/ci.yml
```

### Continuous integration

[.github/workflows/ci.yml](.github/workflows/ci.yml) runs on every push and pull request:

| Job | Steps |
|---|---|
| backend | install → `pytest -q` → `python -m eval.run --min-accuracy 0.85` |
| frontend | `npm ci` → `npm run lint` → `npm run build` |

### Assumptions

- All agent data is mocked. "You" in the fixtures stands for the current user.
- Questions are in English.
- "Issues" alone is ambiguous (both GitHub and Linear have issues), so it triggers
  clarification. "Assigned", "ticket", "sprint" and similar words tip it toward Linear.
- Compound questions are split only on explicit connectors ("and", "also", ";", …).

### Limitations and next steps

- **Keyword routing misses paraphrases** with no overlapping words. Hybrid mode
  addresses this, at the cost of an API call for those questions.
- **Confident keyword false positives are not re-checked** ("Build me a sandwich").
  A next step is escalating weak single-keyword matches too.
- **No conversation state.** A clarification is answered by asking again (the UI
  buttons do this automatically) rather than replying "Linear".
- **No real integrations or auth.** Agents read local JSON fixtures. Real GitHub or
  Linear clients could replace the fixture loader behind the same agent interface.

---

## 4. Frontend

React 19 + TypeScript + Tailwind CSS v4, built with Vite.

### Run the frontend

With the backend running on :8000:

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxies /api to :8000)
npm run build        # type-check + production build
npm run lint         # oxlint
```

For a separately hosted backend, set `VITE_API_URL` before building. In Docker the UI is
served on http://localhost:3000.

### Screens

**Home.** The sidebar lists the agents and their capabilities (loaded from
`/api/agents`), backend status, running counts of each outcome, and the routing mode.
Example questions can be clicked to try the router.

![Home screen with example questions](docs/screenshots/ui-home.png)

**Routed answer with "Why this answer?"** Answers render as cards with status badges.
The panel shows each agent's score bar, the matched keywords, the strategy, the decision
and the capability that answered.

![Routed GitHub answer with the routing trace open](docs/screenshots/ui-routed-trace.png)

**Linear answer.** *"What issues are assigned to me?"* routes to Linear's
`assigned_issues` capability.

![Linear answer for assigned issues](docs/screenshots/ui-linear.png)

**Clarification.** *"Show my issues"* fits both tools, so the router asks. Each
candidate is a button.

![Clarification with GitHub and Linear buttons](docs/screenshots/ui-clarify.png)

Clicking **Linear** asks again as *"show my issues in Linear"*:

![Clarification resolved to Linear](docs/screenshots/ui-clarify-resolved.png)

**Out of scope.** The router declines with the exact required message, and the trace
shows why (no agent had enough evidence).

![Fallback for an out-of-scope question](docs/screenshots/ui-fallback.png)

**Multi-part question.** One section per part, each with its own agent, capability and
trace.

![Compound question answered by GitHub and Linear](docs/screenshots/ui-multi.png)

**Dark theme.** Toggle in the header; the choice is remembered.

![Dark theme](docs/screenshots/ui-dark.png)

---

## 5. Command reference

| Where | Command | Purpose |
|---|---|---|
| `backend/` | `python3 -m venv .venv && source .venv/bin/activate` | Create and activate a virtualenv |
| `backend/` | `pip install -r requirements-dev.txt` | Install the app and test dependencies |
| `backend/` | `pip install -r requirements-llm.txt` | Add the Anthropic SDK for hybrid mode |
| `backend/` | `uvicorn app.main:app --reload` | API on :8000, docs at `/docs` |
| `backend/` | `python -m app.cli` | Interactive CLI |
| `backend/` | `python -m app.cli --trace "question"` | One question with the routing trace |
| `backend/` | `pytest -v` | Run the tests |
| `backend/` | `python -m eval.run` | Routing accuracy report |
| `backend/` | `python -m eval.run --all` | Report every case, not only misses |
| `backend/` | `python -m eval.run --strategy hybrid` | Accuracy with Claude escalation |
| `frontend/` | `npm install` | Install dependencies |
| `frontend/` | `npm run dev` | Dev server on :5173 |
| `frontend/` | `npm run build` | Type-check and build |
| `frontend/` | `npm run lint` | Lint |
| repo root | `docker compose up --build -d` | Start API (:8000) and UI (:3000) |
| repo root | `docker compose logs -f backend` | Follow routing logs |
| repo root | `docker compose down` | Stop everything |
