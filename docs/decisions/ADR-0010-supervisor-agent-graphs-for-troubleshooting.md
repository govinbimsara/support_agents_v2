# ADR-0010: Chat routing: Supervisor agent; graphs only for troubleshooting
- Status: Accepted (seeded from SRS v0.2 Appendix A)
- Date: 2026-11-14
- Requirements: SDD 6, 7

## Context
Options were considered during design and replaced; recorded so they are not reintroduced by mistake.
Documented: Supervisor agent routing; graphs only for troubleshooting (SRS Appendix A; SDD 6.1). Fallback: intent classifier inside the Supervisor.

Likely reasons (confirm): free-form chat is open-ended and fits an LLM router; graphs give deterministic, auditable steps only where the process is fixed.

## Decision
Supervisor agent routes to kb/troubleshoot specialists; ADK graph YAML flows used only for troubleshooting.

## Alternatives considered (superseded)
Graph-based routing for the whole chat

## Consequences
Revisit when the related spikes report back (docs/spikes/STATUS.md).
