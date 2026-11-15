# Claude Code kit for this repo
Guide to the `.claude/` setup, CLAUDE.md, hooks and CI trigger. (Moved here from the root README.)

## What is where
```
CLAUDE.md                 Always-loaded project context (short on purpose; SDD 25.5)
CONSTRAINTS.md            Quality bar skeleton, filled in by the /constraints interview
.env.example              Variable names only. Real .env is git-ignored and denied to Claude
.claude/
  settings.json           Permissions (deny .env etc.) + PreToolUse hook
  hooks/block_env_access.py   Blocks any tool call touching .env / dumping env
  rules/                  secrets.md (always) + path-scoped python/testing/ADK/prompts/workflow rules
  skills/                 15 curated skills from addyosmani/agent-skills (MIT) - loaded
  skills-optional/        Not loaded: frontend-ui-engineering, interview-me, code-simplification,
                          shipping-and-launch, context-engineering (+ code-simplify command)
  agents/                 code-reviewer, security-auditor, test-engineer personas
  commands/               /spec /plan-tasks /build /test /code-review /constraints /ship
  references/ docs/       Checklists the skills link to
docs/
  source-docs/            SRS, SDD, Doc 3-5 as markdown (you add these)
  decisions/              ADR-0001..0013 seeded from SRS Appendix A + template
  spikes/STATUS.md        The 17 spikes with result column
tasks/                    plan.md / todo.md land here (created by /plan-tasks)
.github/workflows/        ci.yml (SDD 25.3, self-activating) and claude.yml (owner-only @claude trigger)
.gitleaks.toml, .pre-commit-config.yaml, .gitignore
```

## Design choices
- **Curated, not everything.** Only skills useful for a Python/ADK/FastAPI backend are loaded; every loaded skill costs description tokens on a Pro quota. `using-agent-skills` (router), performance, deprecation, idea-refine and browser-testing skills were left out.
- **Renamed commands:** upstream `/review` clashes with Claude Code's built-in, and `/plan` with plan mode, so they are `/code-review` and `/plan-tasks`. The `agent-skills:` plugin prefix was stripped because these are project-level skills.
- **JS/TS bias:** upstream skills use TypeScript examples. `CLAUDE.md` tells Claude to translate to the Python toolchain; `/constraints` will propose Python tools (ruff, mypy, pytest-cov, gitleaks).
- **Secrets, three layers:** `permissions.deny`, the PreToolUse hook, and the CLAUDE.md/rules instruction; plus gitleaks in pre-commit and CI. Deny rules alone have had enforcement gaps, hence the hook.
- **Review is manual:** commenting `@claude review this PR ...` as the repo owner triggers the Action. Nothing runs on every push, so the Pro quota is spent only when you decide.

## Verify on first run (not confirmed offline)
1. `/memory` lists CLAUDE.md and the rules; `paths:`-scoped rules should show only when matching files are touched.
2. `/skills` lists the 15 skills; typing `/` shows the 7 commands.
3. `/permissions` shows the deny rules, and the dummy-`.env` test from the local setup guide (step 9) is refused.
4. First `@claude` comment on a PR: check the Action log to see whether the repo's `.claude/skills` and `agents` were picked up. If not, put the review checklist in the prompt.
5. Action tags (`@v4`, `@v5`, `@v2`, `@v1`, neon `@v6`/`@v3`) were written from memory: run `pinact` or let Dependabot pin to SHAs, and check Neon action versions.


## Known loose ends
- A few vendored skills mention skills that were deliberately left out (performance-optimization, deprecation-and-migration, browser-testing-with-devtools). Claude will find nothing there; harmless. Copy them from upstream if you later want them.
- `.claude/skills-optional/` is not loaded. To enable one: `mv .claude/skills-optional/<name> .claude/skills/`; for `/code-simplify`: `mv .claude/skills-optional/code-simplify.command.md .claude/commands/code-simplify.md`.
