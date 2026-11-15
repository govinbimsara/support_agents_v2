# CONSTRAINTS.md - this project's quality bar

> Proposed defaults accepted by Govin on 2026-11-15; refine with `/constraints` (constraint-driven-development skill).

| Dimension | Check (tool) | Proposed threshold | Blocks merge? | Decided? |
|---|---|---|---|---|
| Lint / format | ruff check, ruff format --check | zero errors | yes | yes (default) |
| Types (core modules) | mypy on sessions, tools, guardrails, kb | zero errors | yes | yes (default) |
| Unit tests | pytest -m unit | all pass | yes | yes (default) |
| Coverage (changed lines) | pytest-cov | >= 80% | yes | yes (default) |
| Secrets | gitleaks | zero findings | yes | yes (default) |
| Flow YAML valid | scripts/validate_flows.py | all valid | yes | yes (default) |
| Prompt version header | scripts/check_prompts.py | = prompts.spec_version | yes | yes (default) |
| Config loads (dev/demo/prod) | scripts/check_config.py | all load | yes | yes (default) |
| /ops absent from images | docker build + check | absent | yes | yes (default) |
| Voice latency (NFR-PRF-*) | spike measurements | per SRS | no (manual) | yes (default) |

## Floor (never lowered silently)
No skipped/deleted tests, no new `# type: ignore` / `# noqa` without a reason comment, no thresholds edited down, no stubs shipped as done.
