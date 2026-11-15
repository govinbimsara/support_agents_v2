# support_agents_v2

AI chat and voice support agent for Genie Business (Dialog Pay Business) merchants, in English, Sinhala and Tamil. Proof of concept, v2.

## What it does
- **Chat** (FastAPI): a Supervisor agent routes questions to knowledge-base and troubleshooting specialists.
- **Voice** (LiveKit Cloud): a single Gemini Live agent answers calls, using the same specialists as tools.
- **Shared state**: ADK sessions and a pgvector knowledge base on Neon Postgres.
- **Guardrails**: Model Armor, guardrail prompts and Gemini safety settings. Self-harm and distress are handled with fixed, reviewed texts.
- **Admin portal**: knowledge-base documents, troubleshooting flows, indexing and reporting.

## Stack
Python, uv, FastAPI, Google ADK 2.13, Gemini, LiveKit, Neon Postgres + pgvector, AWS S3, Langfuse, React + Vite + TypeScript (web).

## Repository layout
```
app/        chat API, agents, tools, prompts, config   (coming)
web/        front end                                   (coming)
tests/      unit, integration, behaviour, guardrail
docs/       requirements, design, test specs, ADRs, spike status
```

## Documentation
- Requirements, design and test specifications (SRS, SDD, behaviour tests, guardrail tests, prompt specification) are maintained outside this repository and referenced by ID (FR-*, NFR-*, TC-*, GTS-*).
- `docs/decisions/` - architecture decision records
- `docs/spikes/STATUS.md` - technical spike results
- `CONSTRAINTS.md` - quality bar enforced in CI

## Getting started
Application code has not been added yet. Environment variables are listed in `.env.example`; never commit a real `.env`.

## Contributing and security
See `SECURITY.md`. Please open an issue before large changes.

## License
Apache License 2.0. See `LICENSE` and `NOTICE`.
