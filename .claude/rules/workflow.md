# Development workflow (which skill when)
| Stage | Command / skill | Notes |
|---|---|---|
| Define a slice | `/spec` (spec-driven-development) | Delta spec `SPEC-<slice>.md`; the SRS/SDD stay the source of truth |
| Break down | `/plan-tasks` | Writes `tasks/plan.md`, `tasks/todo.md` |
| Implement | `/build` | ONE task then stop. Use `/build auto` only after the quality bar exists |
| Verify | `/test` | TDD; prove-it pattern for bugs |
| Review | `/code-review` | Five-axis review. `/ship` fans out code-reviewer + security-auditor + test-engineer |
| Quality bar | `/constraints` | Maintains CONSTRAINTS.md |
| Always-on posture | source-driven (cite docs), doubt-driven (for risky decisions), git-workflow, documentation-and-adrs |
Plan mode (Shift+Tab) before anything touching sessions, guardrails, DB schema or CI.
Record any architectural decision as an ADR in `docs/decisions/`.
