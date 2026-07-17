# AI Hunger Games

AI Hunger Games is a Python experiment for studying how LLM-driven personalities answer the same questions, vote on anonymous answers, score over rounds, and are replaced after elimination.

It is an experiment harness, not evidence of social intent. A single generation can show answer generation, anonymous voting, scoring, elimination, and replacement. It cannot demonstrate an alliance, collusion, or genuine evolutionary improvement. The analysis layer reports descriptive indicators and explicit cautions instead of making those claims.

## What runs today

- Eight starting agents with distinct reasoning strategies and eight varied questions.
- Concurrent answer generation with a bounded concurrency policy.
- Anonymous candidate order and no self-voting.
- Sequential voting to reduce constrained-tier Groq pressure.
- Per-operation timeout, application-owned retry/backoff, and `retry-after` support.
- Atomic persistence of games, agents, final populations, rounds, answers, votes, scores, eliminations, replacements, and randomization seeds.
- New experiments pin a provider and snapshot their baseline population,
  questions, policies, and seeds before the first generation runs.
- Multi-generation runs that resume from the prior final population and assign unique replacement IDs.
- Deterministic historical analysis for score trends, voter-target rates, reciprocity indicators, replacement outcomes, and personality diversity.
- A FastAPI API and a React dashboard for running and inspecting experiments.

## Architecture

```text
CLI / Dashboard / API
        |
  generations.py
        |
     engine.py <---- providers.py / groq_providers.py
        |
 repositories.py <---- SQLAlchemy async ORM <---- SQLite + Alembic
        |
   history.py -> analysis.py
```

The boundaries matter:

- The engine owns game rules, retries, and anonymity.
- Providers only communicate with a model or simulate it; they do not persist data.
- Repositories write and load historical facts atomically, rejecting stale
  populations, provider changes, and mutable configuration drift.
- The analysis module consumes immutable history snapshots and makes no database or LLM calls.
- The API maps snapshots into Pydantic response models; it never exposes ORM objects directly.

## Setup

Python 3.12+ and `uv` are required.

```bash
uv sync --all-groups
cp .env.example .env
```

For offline development, keep this setting in `.env`:

```dotenv
USE_REAL_LLM=false
```

For Groq runs, set a real API key and enable the provider:

```dotenv
GROQ_API_KEY=your-key
GROQ_MODEL=openai/gpt-oss-20b
USE_REAL_LLM=true
```

`.env` is ignored by Git and must not be committed. The configured default is `openai/gpt-oss-20b`. As of July 2026, Groq lists `llama-3.1-8b-instant` for shutdown on August 16, 2026; update an older local `.env` before using a real run. See Groq's [model page](https://console.groq.com/docs/model/openai/gpt-oss-20b) and [deprecation notice](https://console.groq.com/docs/deprecations).

## Run an experiment

Run all tests first:

```bash
uv run pytest -v
```

Start a new offline experiment and complete one generation:

```bash
USE_REAL_LLM=false uv run python -m ai_hunger_games.main \
  --new-experiment "Eight-agent baseline"
```

List saved experiments:

```bash
USE_REAL_LLM=false uv run python -m ai_hunger_games.main --list-experiments
```

Resume a specific experiment for multiple generations:

```bash
USE_REAL_LLM=false uv run python -m ai_hunger_games.main \
  --experiment-id 2 \
  --generations 3
```

The command prints each completed generation, including its persisted database ID. A new experiment snapshots the eight sample agents and all run inputs. A resumed experiment loads its latest final-population snapshot, so the prior replacement participates in the next generation. Imported legacy histories remain available for inspection, but cannot be resumed because their original provider and baseline configuration were not recorded.

## Dashboard and API

Start the local server in offline mode. The explicit loopback host keeps this
research tool on the current machine:

```bash
USE_REAL_LLM=false uv run uvicorn ai_hunger_games.api:app \
  --host 127.0.0.1 \
  --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The dashboard can create experiments, run one durable generation per request, inspect anonymous round records, review retry/failure telemetry and score/replacement history, and view voter-target rates against their random baseline.

### React dashboard development

The browser source lives in `frontend/`. It uses React 19, TypeScript, Vite,
TanStack Query, Radix UI primitives, Lucide icons, and Recharts. These are
free, open-source packages: Radix supplies accessible unstyled behavior while
the project owns the visual design.

Vite 8 requires Node 20.19+ or 22.12+; this project was verified with Node
24.18. Install the exact versions recorded in the lockfile:

```bash
cd frontend
npm ci
```

Use `npm install` only when intentionally changing frontend dependencies, then
commit the resulting `package-lock.json` update.

For the fastest editing loop, start the FastAPI server above in one terminal,
then start Vite in another. Its development proxy forwards the API paths to
FastAPI on port 8000:

```bash
cd frontend
npm run dev
```

For the Python server to serve the production dashboard, build it after any
frontend change:

```bash
cd frontend
npm run build
```

The build writes immutable browser assets to `src/ai_hunger_games/web/`, which
FastAPI serves under `/static/`. This keeps the deployed application
same-origin and avoids a CORS configuration. The round-explorer API types keep
answers anonymous: they contain candidate IDs and content, never answer-author
or selected-agent IDs.

The public API routes are:

```text
GET  /health
POST /experiments
GET  /experiments
GET  /experiments/{experiment_id}
POST /experiments/{experiment_id}/generations
GET  /experiments/{experiment_id}/generations
GET  /experiments/{experiment_id}/analysis
GET  /generations/{game_id}
GET  /generations/{game_id}/rounds
GET  /generations/{game_id}/votes
```

The in-process run coordinator prevents two dashboard requests from running the same experiment concurrently. The repository also rejects a stale generation plan at save time, so a slow provider call cannot silently claim the wrong generation number.

The API has no authentication or authorization layer. Keep it bound to
`127.0.0.1` and do not expose it to a network while it has access to a Groq API
key or local experiment history.

## Persistence and migrations

The default database is `data/ai_hunger_games.db`. It is an experiment record: do not delete it to resolve a problem.

For a non-destructive snapshot, use Python's SQLite backup API. Choose a new
destination filename for each snapshot:

```python
import sqlite3

source = sqlite3.connect("data/ai_hunger_games.db")
destination = sqlite3.connect("data/ai_hunger_games.backup.db")
try:
    source.backup(destination)
finally:
    destination.close()
    source.close()
```

The backup API works while other clients access the source database. Verify
referential integrity without changing data:

```bash
uv run python -m sqlite3 data/ai_hunger_games.db "PRAGMA foreign_key_check;"
```

No output from `foreign_key_check` means SQLite found no broken foreign-key
references. Python documents the [SQLite backup API](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup), and SQLite documents [foreign-key enforcement](https://www.sqlite.org/foreignkeys.html).

The application runs Alembic migrations at startup. The explicit commands are:

```bash
uv run alembic upgrade head
uv run alembic current
uv run alembic check
```

The schema contains:

```text
experiments
experiment_configurations
experiment_initial_agents
games
game_agents
game_final_agents
rounds
answers
answer_failures
votes
round_scores
```

Historical unscoped databases are safely imported into one `Imported legacy history` experiment by migration `0006`. This preserves the old rows without pretending that separate historical runs had known experiment boundaries.

Migrations `0007` through `0010` add answer retry/failure telemetry, make every game physically experiment-scoped, snapshot inputs for newly created experiments, and repair the experiment-name uniqueness boundary in historically stamped databases. SQLite batch migrations temporarily disable foreign-key enforcement only while the referenced table is copied, then run `PRAGMA foreign_key_check`; this prevents child rows from cascading away during the rebuild.

One `save_game()` transaction writes a complete generation. A database constraint failure rolls it back; repository tests verify that no partial game remains. SQLite foreign keys are enabled for every connection.

## Rate limits and real-provider behavior

Groq SDK retries are disabled with `AsyncGroq(max_retries=0)`. The engine is the only retry owner, which keeps attempt counts, timeout behavior, backoff, and provider `retry-after` handling understandable.

Answers may be concurrent, but the configured production policy limits that concurrency. Votes remain sequential because voting requests otherwise create avoidable token-per-minute pressure on constrained tiers. The current model-specific quota should be checked in the Groq console before tuning these values. Groq documents request throttling and HTTP `429` rate-limit responses as application responsibilities in its [rate-limit documentation](https://console.groq.com/docs/rate-limits).

Unit and repository tests use simulated providers only. A real run is opt-in through `USE_REAL_LLM=true`; natural-language output is intentionally not asserted exactly.

## Analysis interpretation

For each voter-target pair, the analysis stores:

```text
observed votes
eligible voting opportunities
observed rate
expected random-vote rate
excess votes over that baseline
```

The denominator is the actual number of eligible answers in each persisted round, so partial-answer rounds do not use a fictional eight-agent baseline. Reciprocity, stable clusters, and post-entry changes are called indicators only. They should be compared with random and simulated baselines over many generations before making a behavioral claim.

## Tests

The suite covers:

- Game validation, anonymity, candidate construction, scoring, elimination, concurrency, retries, and cancellation.
- Groq response parsing and anonymous vote prompts.
- Temporary SQLite migrations, schema initialization, command-line migration preservation, transaction rollback, final-population loading, scoped generations, and stale-plan rejection.
- Multi-generation chaining and replacement IDs.
- Deterministic analysis metrics and invalid-history rejection.
- FastAPI routes, a simulated eight-agent generation, and static dashboard delivery.
- React component behavior for experiment creation and anonymous round rendering.

Frontend verification commands are:

```bash
cd frontend
npm run check
npm test
npm run build
```

## Continuous integration

[`ci.yml`](.github/workflows/ci.yml) runs for every push and pull request. It
tests the Python package on 3.12 and 3.14, runs Ruff linting and formatting,
verifies Alembic metadata, builds a wheel, and separately type-checks, tests,
and builds the React dashboard on Node 24. The frontend job fails if its build
would change the committed assets under `src/ai_hunger_games/web/`; FastAPI
therefore cannot accidentally serve a stale dashboard bundle.

Before opening a change for review, run the same checks locally one command at
a time:

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run ruff format --check .
uv run pytest -v
uv run alembic check
```

Then, in `frontend/`:

```bash
npm ci
npm run check
npm test
npm run build
git diff --exit-code -- ../src/ai_hunger_games/web
```

Ruff uses a narrow initial rule set for import correctness and conventional
Python errors. Its formatter provides one deterministic style, while the
focused rules avoid turning this release-readiness step into an unrelated
architecture rewrite.

The implementation follows SQLAlchemy's async `AsyncSession` pattern with the `sqlite+aiosqlite` dialect. Reference: [SQLAlchemy asyncio documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html). The API uses FastAPI's lifespan mechanism for database setup and teardown: [FastAPI lifespan documentation](https://fastapi.tiangolo.com/advanced/events/).

Frontend references: [React](https://react.dev/), [Vite](https://vite.dev/guide/), [TanStack Query](https://tanstack.com/query/v5/docs/framework/react/installation), [Radix UI](https://www.radix-ui.com/primitives/docs/overview/introduction), [Lucide](https://lucide.dev/), and [Recharts](https://recharts.github.io/en-US/guide/).
