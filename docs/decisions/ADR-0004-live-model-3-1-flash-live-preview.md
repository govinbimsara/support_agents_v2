# ADR-0004: Voice model: gemini-3.1-flash-live-preview
- Status: Accepted (seeded from SRS v0.2 Appendix A)
- Date: 2026-11-14
- Requirements: SRS 3.8, MVP-12

## Context
Options were considered during design and replaced; recorded so they are not reintroduced by mistake.
Documented: 3.1 Flash Live is a legacy preview; Gemini 3.8 Live is not used because of voice and accent-change issues observed by the team; re-evaluate at MVP (SRS 3.x, MVP-12).

Consequence documented: preview model behaviour may change; model name comes from config; failover configured (FR-AGT-10).

## Decision
gemini-3.1-flash-live-preview; re-evaluate at MVP (MVP-12). Preview status is a known constraint.

## Alternatives considered (superseded)
Gemini 3.8 Live (voice and accent-change issues)

## Consequences
Revisit when the related spikes report back (docs/spikes/STATUS.md).
