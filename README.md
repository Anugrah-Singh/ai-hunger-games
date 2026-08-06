# AI Hunger Games

A full-stack TypeScript application where eight distinct AI personalities answer a question, anonymously judge the other answers, and eliminate one competitor each round until a single winner remains.

The backend is provider-agnostic. Game logic depends on an internal `LlmClient` interface instead of a vendor SDK, while adapters connect that interface to the Vercel AI SDK and supported model providers.

## Highlights

- Strict TypeScript across API, browser client, contracts, and tests
- Fastify API with Zod validation and a common JSON error envelope
- React 19 client built with Vite and Tailwind CSS 4
- Native adapters for OpenAI, Anthropic, and Google
- Generic OpenAI-compatible adapter for services such as Hugging Face, Groq, OpenRouter, Ollama, LM Studio, Together AI, Fireworks, or a private gateway
- Structured vote generation with defensive JSON fallback
- Bounded concurrent model calls instead of slow sequential generation
- Anonymous voting prompts that never expose answer authors
- Deterministic vote fallbacks that can be reproduced in tests
- Optional disabled, in-memory, or atomic Redis request tracking
- Health, readiness, status, reset, answer, and voting endpoints
- Unit and integration tests that do not spend provider credits

## Architecture

```text
apps/web
  React UI
      │
      ▼
packages/contracts
  Zod schemas + inferred TypeScript types
      │
      ▼
apps/api
  Fastify routes
      │
      ▼
Application services
  AnswerService / VoteService
      │
      ▼
LlmClient interface
      │
      ├── OpenAI adapter
      ├── Anthropic adapter
      ├── Google adapter
      ├── OpenAI-compatible adapter
      └── Deterministic mock adapter
```

Routes, services, tests, and the frontend do not import provider SDKs. Only the provider registry knows how a configured provider is constructed.

## Requirements

- Node.js 24 LTS
- npm 12 or a compatible npm release
- An API key for the selected hosted provider, unless using a local endpoint that does not require authentication
- Redis 7.2 or newer only when `REQUEST_TRACKING_MODE=redis`

## Installation

```bash
npm install
cp .env.example .env
```

Edit `.env` and choose a provider configuration.

Start both applications:

```bash
npm run dev
```

You can also run them independently with `npm run dev:api` and `npm run dev:web`.

The default local addresses are:

- Web: `http://localhost:5173`
- API: `http://localhost:5000`

## Provider configuration

### OpenAI

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-5-mini
LLM_API_KEY=replace-me
```

### Anthropic

```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-5
LLM_API_KEY=replace-me
```

### Google

```env
LLM_PROVIDER=google
LLM_MODEL=gemini-2.5-flash
LLM_API_KEY=replace-me
```

### Hugging Face router

```env
LLM_PROVIDER=openai-compatible
LLM_PROVIDER_NAME=huggingface
LLM_BASE_URL=https://router.huggingface.co/v1
LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.2
LLM_API_KEY=replace-me
LLM_SUPPORTS_STRUCTURED_OUTPUTS=true
```

### Any OpenAI-compatible endpoint

```env
LLM_PROVIDER=openai-compatible
LLM_PROVIDER_NAME=my-provider
LLM_BASE_URL=https://provider.example/v1
LLM_MODEL=model-id
LLM_API_KEY=replace-me
LLM_SUPPORTS_STRUCTURED_OUTPUTS=false
```

For a local Ollama or LM Studio endpoint, use its OpenAI-compatible base URL. `LLM_API_KEY` may be omitted when the local server does not require it.

### Offline mock mode

```env
LLM_PROVIDER=mock
LLM_MODEL=deterministic-local-model
```

Mock mode is useful for UI development and does not make external requests.

## Environment variables

| Variable                          | Purpose                                     | Default                 |
| --------------------------------- | ------------------------------------------- | ----------------------- |
| `NODE_ENV`                        | `development`, `test`, or `production`      | `development`           |
| `HOST`                            | API bind address                            | `0.0.0.0`               |
| `PORT`                            | API port                                    | `5000`                  |
| `WEB_ORIGINS`                     | Comma-separated browser origins             | `http://localhost:5173` |
| `TRUST_PROXY`                     | Trust reverse-proxy headers                 | `false`                 |
| `LLM_PROVIDER`                    | Provider adapter                            | `openai-compatible`     |
| `LLM_PROVIDER_NAME`               | Identifier for compatible providers         | `custom`                |
| `LLM_MODEL`                       | Provider model ID                           | Mistral example         |
| `LLM_API_KEY`                     | Provider credential                         | none                    |
| `LLM_BASE_URL`                    | Required by compatible providers            | none                    |
| `LLM_SUPPORTS_STRUCTURED_OUTPUTS` | Advertise strict structured-output support  | `false`                 |
| `AI_TIMEOUT_MS`                   | Maximum duration of each model call         | `30000`                 |
| `AI_MAX_RETRIES`                  | SDK retries for transient provider failures | `2`                     |
| `AI_CONCURRENCY`                  | Maximum concurrent generation calls         | `3`                     |
| `REQUEST_TRACKING_MODE`           | `disabled`, `memory`, or `redis`            | `memory`                |
| `REQUEST_LIMIT`                   | Logical API-call budget                     | `200`                   |
| `REDIS_URL`                       | Redis connection URL                        | none                    |
| `COUNTER_FAILURE_MODE`            | `open` or `closed` on Redis failure         | `closed`                |
| `ADMIN_KEY`                       | Secret for resetting the global counter     | none                    |
| `HTTP_RATE_LIMIT`                 | Per-IP requests per window                  | `60`                    |
| `HTTP_RATE_WINDOW_MS`             | Per-IP rate-limit window                    | `60000`                 |
| `VITE_API_URL`                    | Browser-facing API URL                      | same origin             |

In production, `ADMIN_KEY` is required whenever request tracking is enabled.

## Request tracking

### Disabled

No global usage count is recorded. Requests remain protected by the per-IP HTTP rate limiter.

```env
REQUEST_TRACKING_MODE=disabled
```

### Memory

The count lives in the API process and resets whenever the process restarts. This is suitable for local development and single-instance demonstrations.

```env
REQUEST_TRACKING_MODE=memory
REQUEST_LIMIT=200
```

### Redis

The count is shared across API instances. A Lua script makes the consume-and-disable decision atomic.

```env
REQUEST_TRACKING_MODE=redis
REQUEST_LIMIT=200
REDIS_URL=redis://localhost:6379
COUNTER_FAILURE_MODE=closed
```

`COUNTER_FAILURE_MODE=open` permits AI calls when Redis is unavailable. `closed` rejects them with `503` so cost controls cannot silently disappear.

## API

### Generate answers

```http
POST /api/answers
Content-Type: application/json
```

```json
{
  "question": "What makes a decision fair?",
  "personalities": [
    { "id": 1, "name": "The Philosopher", "trait": "Questions assumptions" },
    { "id": 2, "name": "The Pragmatist", "trait": "Focuses on results" }
  ]
}
```

### Generate votes

```http
POST /api/vote
Content-Type: application/json
```

```json
{
  "question": "What makes a decision fair?",
  "responses": [
    { "id": 1, "answer": "Answer one" },
    { "id": 2, "answer": "Answer two" }
  ]
}
```

### Usage status

```http
GET /api/status
```

### Reset usage counter

```http
POST /api/reset-counter
X-Admin-Key: your-admin-key
```

### Operational endpoints

```text
GET /health
GET /ready
GET /ping
```

`/health` is a lightweight liveness check. `/ready` checks required application dependencies without exposing credentials.

## Commands

```bash
npm run dev           # API and frontend development servers
npm run dev:api       # API development server
npm run dev:web       # frontend development server
npm run format        # format all supported files
npm run lint          # lint TypeScript and TSX
npm run typecheck     # type-check every workspace
npm run test          # run all tests
npm run build         # build contracts, API, and frontend
npm run verify        # run all quality gates
```

## Production build

```bash
npm install
npm run verify
npm run start --workspace @ai-hunger-games/api
```

Serve `apps/web/dist` through a static host or reverse proxy and set `VITE_API_URL` before building when the API is deployed at a different origin.

## Security notes

- Do not expose `ADMIN_KEY` to the browser.
- Keep provider keys only in the API environment.
- Configure `WEB_ORIGINS` explicitly in production.
- Use Redis-backed tracking for multiple API replicas.
- Choose `COUNTER_FAILURE_MODE=closed` when the global request budget is a hard cost boundary.
- Health responses intentionally omit API-key and connection details.

## Licence

MIT. See `LICENSE` for the required notices covering the supplied source and this TypeScript rewrite.

# ai-hunger-games
