# ADR-0011: Voice: single Live agent calling specialists as tools
- Status: Accepted (seeded from SRS v0.2 Appendix A)
- Date: 2026-11-14
- Requirements: SDD 20

## Context
Options were considered during design and replaced; recorded so they are not reintroduced by mistake.
Documented: voice transfer_to_agent has known live hand-off defects; specialists run as AgentTool; retest on 2.13 (SDD 6.2, spike 6).

Consequence: kb_agent_en serves voice in every language; the Live agent speaks the English result in the stored language (FR-LANG-10).

## Decision
One Live agent; specialists exposed as tools (spike 4, 6).

## Alternatives considered (superseded)
Voice multi-agent hand-offs (transfer_to_agent)

## Consequences
Revisit when the related spikes report back (docs/spikes/STATUS.md).
