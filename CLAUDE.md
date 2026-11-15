# Genie Business Support Agent POC

Chat + voice support agent for Dialog Pay Business merchants (English / Sinhala / Tamil). Solo-built POC; the codebase is handed to a team after the demo, so keep it readable and documented.
Specs (SRS v0.2, SDD v0.3, Doc 3 behaviour tests, Doc 4 guardrail tests, Doc 5 prompts) live in `docs/source-docs/` as LOCAL, git-ignored markdown copies; never commit them or quote large parts of them in committed files. Decisions: `docs/decisions/`. Spike results: `docs/spikes/STATUS.md`. Quality bar: `CONSTRAINTS.md`.

## Architecture map
chat API (FastAPI, Railway SG) | voice worker (ADK LiveKitRunner, LiveKit Cloud) | Neon Postgres (ADK sessions + pgvector KB) | AWS S3 | Gemini | Model Armor | Langfuse (OTel)

## Key rules (never break without an ADR)
- Language changes ONLY via the `set_language` tool; never detect per message.
- All tunables in `app/config/config.yaml`; never hard-code.
- Never write to `adk.*` tables directly. Never change the ADK pin without a Neon-branch test.
- Prompts live in `app/prompts` and must match Doc 5 (version header = `prompts.spec_version`). Do not edit prompt text or guardrail thresholds unless the task says so.
- Flow steps must be idempotent (FR-TS-07).
- `/ops` is never imported by app code or included in images.
- Check the SRS/SDD before inventing behaviour. Reference requirement IDs (FR-*, NFR-*, TC-*, GTS-*) in commits, PR titles and tests.

## SECURITY: secrets (hard rule)
- NEVER read, print, grep, cat, or open `.env` or any `.env.*` file (only `.env.example` is allowed). Not to debug, not to "check a value".
- Never echo environment variables or print secrets. If a credential is missing or wrong, tell the user which variable name to fix and stop.
- Never commit secrets. Config loads from environment; `.env` is git-ignored and denied in `.claude/settings.json`.

## Commands
- Install: `uv sync` (Python 3.14, pinned in `.python-version`)
- Lint + format: `uv run ruff check . && uv run ruff format --check .` (fix: `uv run ruff check --fix . && uv run ruff format .`)
- Types (CI scope): `uv run mypy app/sessions app/tools app/guardrails app/kb`
- Unit tests: `uv run pytest -m unit`
- Integration tests: `uv run pytest -m integration` (needs a Neon branch; exits 5 while there are none)
- Run chat API / voice worker: added with the API and voice slices
- Config overrides: `GENIE_<KEY>=value`, nested `GENIE_<SECTION>__<KEY>` (see `app/config/loader.py`)

## Workflow
- One requirement group per slice: `/spec` -> `/plan-tasks` -> `/build` (one task, then stop) -> `/test` -> `/code-review` -> PR. Details in `.claude/rules/workflow.md`.
- Skills are written with JS/TS examples; translate to Python (uv, pytest, ruff, mypy, FastAPI). Use the `context7` MCP for current ADK / LiveKit / FastAPI / Neon docs instead of memory.
- Work on a feature branch; never push to `main`. Small commits, conventional messages.

## Testing
Test IDs map to TC-* (Doc 3) and GTS-* (Doc 4). Every module ships with unit tests. Never weaken, skip or delete a test to get green.

## Glossary
Supervisor, specialist, Live agent, flow, strike, clip - see SDD glossary.

## Proposed changes pending review
`docs/proposed/spec-patches.md` (SDD 5.4 fix, strike rules, FR-CRS crisis handling) and `docs/proposed/Doc5_PromptSpecification_v0.1-DRAFT.md` are drafts until Govin approves them. Do not treat them as final spec.
