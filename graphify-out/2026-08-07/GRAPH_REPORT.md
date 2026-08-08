# Graph Report - .  (2026-08-07)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 490 nodes · 766 edges · 25 communities (20 shown, 5 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.74)
- Token cost: 918 input · 59 output

## Graph Freshness
- Built from commit: `8dcb12a4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Frontend API Client
- Backend Application Logic
- API TypeScript Configuration
- Project Tooling and Dependencies
- Web Frontend Dependencies
- Data Schemas and Validation
- dependencies
- env.ts
- RequestCounter
- compilerOptions
- compilerOptions
- contracts/package.json
- LlmClient Interface
- text.ts
- error-handler.ts
- vite-env.d.ts
- web/tsconfig.json
- dev.mjs
- tsconfig.json
- main.tsx

## God Nodes (most connected - your core abstractions)
1. `LlmClient` - 21 edges
2. `compilerOptions` - 20 edges
3. `RequestCounter` - 17 edges
4. `AppConfig` - 14 edges
5. `Personality` - 13 edges
6. `CounterStatus` - 12 edges
7. `registerRoutes()` - 12 edges
8. `scripts` - 12 edges
9. `MemoryRequestCounter` - 10 edges
10. `RedisRequestCounter` - 10 edges

## Surprising Connections (you probably didn't know these)
- `exclude` --extends--> `node_modules`  [EXTRACTED]
  packages/contracts/tsconfig.json → apps/api/tsconfig.json
- `BuildAppOptions` --references--> `AppConfig`  [EXTRACTED]
  apps/api/src/app.ts → apps/api/src/config/env.ts
- `BuildAppOptions` --references--> `RequestCounter`  [EXTRACTED]
  apps/api/src/app.ts → apps/api/src/counter/types.ts
- `buildApp()` --calls--> `registerErrorHandling()`  [EXTRACTED]
  apps/api/src/app.ts → apps/api/src/http/error-handler.ts
- `buildApp()` --calls--> `registerRoutes()`  [EXTRACTED]
  apps/api/src/app.ts → apps/api/src/routes/register-routes.ts

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **LLM Adapter Pattern** — llm_client_interface, openai_adapter, anthropic_adapter, google_adapter, openai_compatible_adapter, mock_adapter [EXTRACTED 1.00]
- **Full Stack Application Flow** — apps_web, apps_api, packages_contracts [EXTRACTED 1.00]

## Communities (25 total, 5 thin omitted)

### Community 0 - "Frontend API Client"
Cohesion: 0.07
Nodes (41): api, ApiClientError, baseUrl, readJson(), request(), userMessageFor(), App(), AnswersPanel() (+33 more)

### Community 1 - "Backend Application Logic"
Cohesion: 0.08
Nodes (24): BuildAppOptions, RequestCounterUnavailableError, AppError, consumeQuota(), setQuotaHeaders(), secretsMatch(), parseBody(), MockLlmClient (+16 more)

### Community 2 - "API TypeScript Configuration"
Cohesion: 0.05
Nodes (41): compilerOptions, composite, outDir, rootDir, tsBuildInfoFile, types, exclude, extends (+33 more)

### Community 3 - "Project Tooling and Dependencies"
Cohesion: 0.05
Nodes (39): eslint, @eslint/js, devDependencies, eslint, @eslint/js, prettier, tsx, @types/node (+31 more)

### Community 4 - "Web Frontend Dependencies"
Cohesion: 0.05
Nodes (36): @ai-hunger-games/contracts, @ai-hunger-games/contracts, dependencies, @ai-hunger-games/contracts, lucide-react, react, react-dom, zod (+28 more)

### Community 5 - "Data Schemas and Validation"
Cohesion: 0.07
Nodes (29): AnswersRequest, answersRequestSchema, AnswersResponse, answersResponseSchema, addUniqueIdValidation(), Answer, answerSchema, PersonalityInput (+21 more)

### Community 6 - "dependencies"
Cohesion: 0.06
Nodes (35): ai, @ai-sdk/anthropic, @ai-sdk/google, @ai-sdk/openai, @ai-sdk/openai-compatible, dependencies, ai, @ai-sdk/anthropic (+27 more)

### Community 7 - "env.ts"
Cohesion: 0.10
Nodes (19): buildApp(), createTestApp(), AppConfig, envSchema, loadConfig(), optionalString, optionalUrl, AiSdkLlmClient (+11 more)

### Community 8 - "RequestCounter"
Cohesion: 0.12
Nodes (9): createRequestCounter(), DisabledRequestCounter, MemoryRequestCounter, ConnectedRedisClient, createConnectedRedisClient(), RedisRequestCounter, CounterDecision, CounterStatus (+1 more)

### Community 9 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, declaration, declarationMap, exactOptionalPropertyTypes, forceConsistentCasingInFileNames, isolatedModules, lib, module (+13 more)

### Community 10 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, composite, jsx, lib, module, moduleResolution, noEmit, target (+10 more)

### Community 11 - "contracts/package.json"
Cohesion: 0.12
Nodes (16): dependencies, zod, exports, files, dist, zod, main, name (+8 more)

### Community 12 - "LlmClient Interface"
Cohesion: 0.21
Nodes (11): AnswerService, Anthropic Adapter, Fastify API, React UI, Google Adapter, LlmClient Interface, Mock Adapter, OpenAI Adapter (+3 more)

### Community 13 - "text.ts"
Cohesion: 0.40
Nodes (8): applyKnownCorrections(), extractSentences(), KNOWN_GENERATION_CORRECTIONS, normalizeAnswer(), normalizeGeneratedText(), normalizePunctuationSpacing(), normalizeReason(), normalizeWhitespace()

### Community 14 - "error-handler.ts"
Cohesion: 0.47
Nodes (8): isAppError(), getErrorMessage(), getNumberProperty(), getStringProperty(), hasProperty(), isRecord(), registerErrorHandling(), UnknownRecord

## Knowledge Gaps
- **185 isolated node(s):** `name`, `version`, `private`, `type`, `main` (+180 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LlmClient` connect `Backend Application Logic` to `env.ts`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Why does `dependencies` connect `dependencies` to `Web Frontend Dependencies`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Why does `RequestCounter` connect `RequestCounter` to `Backend Application Logic`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **What connects `name`, `version`, `private` to the rest of the system?**
  _185 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Frontend API Client` be split into smaller, more focused modules?**
  _Cohesion score 0.06994535519125683 - nodes in this community are weakly interconnected._
- **Should `Backend Application Logic` be split into smaller, more focused modules?**
  _Cohesion score 0.08350168350168351 - nodes in this community are weakly interconnected._
- **Should `API TypeScript Configuration` be split into smaller, more focused modules?**
  _Cohesion score 0.046511627906976744 - nodes in this community are weakly interconnected._