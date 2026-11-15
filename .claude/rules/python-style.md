---
paths:
  - "app/**/*.py"
  - "tests/**/*.py"
  - "jobs/**/*.py"
  - "scripts/**/*.py"
---
# Python conventions
- Python managed with `uv`; dependencies pinned via lock file; ADK version pinned once, shared by chat API and voice worker.
- `ruff` for lint + format; type hints everywhere; `mypy` strict on sessions, tools, guardrails, kb.
- FastAPI: pydantic models at every boundary; async all the way down; no blocking calls in the event loop.
- No module-level side effects (no network or DB at import time).
- Config via the loader in `app/config`; never `os.environ[...]` scattered in modules.
- Structured logging; no secrets or full user text in logs (mask per SDD).
