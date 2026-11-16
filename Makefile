# Quality gates for CONSTRAINTS.md. These are convenience wrappers: CONSTRAINTS.md is the
# canonical source for every rule, number and command. If the two disagree, the file wins.
#
#   make check-fast   edit loop, a few seconds     (lint, format, types)
#   make check-task   before handing work back     (+ unit tests, changed-line coverage, floor guard)
#   make check-full   what CI runs                 (+ dependency vulnerabilities, secret scan)
#
# BASE is the branch changes are measured against (changed-line coverage, floor guard).

BASE ?= origin/main
# Mirrors CONSTRAINTS.md "Coverage (changed lines)". Edit the file first, then this.
CHANGED_LINE_COVERAGE ?= 80
MYPY_PATHS := app migrations scripts

.PHONY: check check-fast check-task check-full lint types test coverage floor deps secrets

check: check-task

check-fast: lint types

check-task: check-fast coverage floor

check-full: check-task deps secrets

lint:
	uv run ruff check .
	uv run ruff format --check .

types:
	uv run mypy $(MYPY_PATHS)

test:
	uv run pytest -m unit

# Unit tests with coverage, then the blocking rule: changed lines must be covered.
# The project-wide total is printed for information only and never fails the build.
coverage:
	uv run pytest -m unit --cov --cov-report=term:skip-covered --cov-report=xml:coverage.xml
	uv run diff-cover coverage.xml --compare-branch=$(BASE) --include-untracked \
		--fail-under=$(CHANGED_LINE_COVERAGE)

floor:
	uv run python scripts/floor_guard.py --base $(BASE)

# Dependency vulnerabilities at high severity or above. osv-scanner exits 1 on ANY finding
# (that is expected and handed to the gate); any other non-zero exit is a real scanner error.
deps:
	@if command -v osv-scanner >/dev/null; then \
		osv-scanner scan source -L uv.lock --format json > osv.json || [ $$? -eq 1 ] \
			&& uv run python scripts/check_osv.py osv.json; \
	else \
		echo "deps: SKIPPED, osv-scanner is not installed (CI runs this check)"; \
	fi

# Secret scan of git content ONLY (staged changes and this branch's commits). Deliberately never
# `gitleaks dir`: that walks the working tree and would open local secrets files such as .env.
secrets:
	@if command -v gitleaks >/dev/null; then \
		gitleaks git --staged --redact --no-banner \
			&& gitleaks git --redact --no-banner --log-opts="$(BASE)..HEAD"; \
	else \
		echo "secrets: SKIPPED, gitleaks is not installed (CI and the pre-commit hook run it)"; \
	fi
