# CONSTRAINTS.md - this project's quality bar

> Defaults accepted by Govin on 2026-11-15; enforcement wired up on 2026-11-17 with `/constraints`.
> Agents: read this before writing code, run `make check-task` before handing work back, and never
> weaken this file to make a change pass. Fix the code, or add a dated exception below.
> The commands in the "Checked by" column are canonical; the Makefile and CI mirror them.

## Floor (always enforced, checked on every diff)

Checked by `uv run python scripts/floor_guard.py --base origin/main` (task end, and CI on pull requests).

- No suppression without a reason: a noqa or type-ignore comment needs a second comment on the same line saying why. Coverage, scanner and secret-scan suppressions are never allowed without an exception.
- No skipped or deleted tests: no skip, skipif or xfail markers, no deleted test files, no net loss of assertions.
- No stubs shipped as done: no `NotImplementedError` without a requirement or ticket ID in a comment on the same line, no swallowed exceptions, no bare `...` bodies in `app/`, no open-item markers without a ticket or requirement ID.
- No thresholds edited down: a loosened number, a removed rule or a new exception row in this file fails the guard and needs a human decision.
- No secrets in git: see the Secrets row below.
- This file is never weakened to make a change pass.

## Enforced

| Dimension | Rule | Checked by | Runs at | Why |
|---|---|---|---|---|
| Lint / format | zero errors | `uv run ruff check . && uv run ruff format --check .` | every edit (pre-commit), CI | One style with no review debate; the rule set lives in `pyproject.toml`. |
| Types (core modules) | zero mypy errors, strict, on `app`, `migrations`, `scripts` | `uv run mypy app migrations scripts` | task end, CI | Strict is cheap while the codebase is small and covers the sessions, tools, guardrails and kb core. |
| Unit tests | all pass | `uv run pytest -m unit` | task end, CI | Fast and offline, so they can run on every task. |
| Coverage (changed lines) | >= 80% of changed lines covered (branch coverage, `app/` and `scripts/`) | `uv run pytest -m unit --cov --cov-report=xml:coverage.xml` then `uv run diff-cover coverage.xml --compare-branch=origin/main --include-untracked --fail-under=80` | task end, CI on pull requests | High enough to force a test for new logic, low enough to allow glue lines. A changed-line number is one the author can move; project coverage is inherited. |
| Floor guard | zero findings | `uv run python scripts/floor_guard.py --base origin/main` | task end, CI on pull requests | The cheapest road to green is lowering the bar; this makes that loud. |
| Secrets | zero findings | pre-commit `gitleaks` hook and CI `gitleaks-action` (full history); locally `gitleaks git --staged --redact --no-banner` | every commit, CI | External rule set. Never `gitleaks dir`: it walks the working tree and would open local secrets files. |
| Security: dependencies | no vulnerability group at CVSS 7.0 or above, or with unknown severity | `osv-scanner scan source -L uv.lock --format json > osv.json` then `uv run python scripts/check_osv.py osv.json` | CI (`deps-scan`), `make deps` | External vulnerability database the agent cannot argue with. 7.0 is where CVSS "High" starts; below that is mostly noise for a POC. Unknown fails closed. |
| Flow YAML valid | all valid | `uv run python scripts/validate_flows.py` | CI | Pending: the script lands with the flows slice. The CI step switches on when the file exists. |
| Prompt version header | = prompts.spec_version | `uv run python scripts/check_prompts.py` | CI | Pending: the script lands with the prompts slice (FR-AGT-11). |
| Config loads (dev/demo/prod) | all load | `uv run python scripts/check_config.py` | CI | Pending: the script lands with the config slice. |
| /ops absent from images | absent | CI `images` job: docker build, then `test -e /ops` | CI | NFR-SEC-08. Passes trivially until a Dockerfile exists. |
| Voice latency (NFR-PRF-*) | per SRS | spike measurements in `docs/spikes/STATUS.md` | manual | Needs real audio and a live worker, so it is not a merge gate. |

Block, not warn: every row above fails the task and CI. Dependency and image checks run in CI
only; everything else runs in `make check-task`.

## Where checks run

| Stage | Command | Budget | Today |
|---|---|---|---|
| Edit loop | `make check-fast` (ruff + mypy) | under 5 s | 0.5 s warm cache, about 4 s cold |
| Task end | `make check-task` (+ unit tests, changed-line coverage, floor guard) | under 90 s | about 4.5 s |
| CI | `make check-full` plus the CI-only rows | no limit | n/a |

## Measured, not yet enforced

| Metric | Today (2026-11-17) | Direction |
|---|---|---|
| Project-wide coverage (branch, `app/` + `scripts/`) | 98% (`app/` 100%) | Reported in the CI job summary, never blocking. Make it a ratchet (0.5 point tolerance) once the voice worker exists. |
| Unit test count | 151 | Informational. |

## Not enforced, on purpose

- Accessibility and page performance: there is no web UI to run axe-core or Lighthouse against. Revisit if one appears.
- Code scanning (Semgrep) and import boundaries (import-linter): not selected for the POC. `/ops` isolation is covered by the image check.
- Mutation testing: not selected.

## Exceptions

Owner and expiry are required; the default lifetime is 90 days. A new row fails the floor guard on purpose so a human reads it.

| ID | Rule | Path | Reason | Owner | Expires |
|---|---|---|---|---|---|

No exceptions today.
