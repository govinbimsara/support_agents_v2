# ADR-0007: Realtime media: LiveKit Cloud
- Status: Accepted (seeded from SRS v0.2 Appendix A)
- Date: 2026-11-14
- Requirements: SDD 20 rows 2, 15

## Context
Options were considered during design and replaced; recorded so they are not reintroduced by mistake.
Documented: Railway self-hosted LiveKit is TCP only; LiveKit Cloud provides UDP and TURN. Railway outbound IPv6 is off by default (SDD 20 row 2).

Fallback documented: worker on Railway Singapore if Cloud latency to Neon is poor (spike 2); free plan limits tested in spike 15.

## Decision
LiveKit Cloud (UDP, TURN included). Fallback: worker on Railway SG (spike 2).

## Alternatives considered (superseded)
Railway self-hosted LiveKit server (TCP only)

## Consequences
Revisit when the related spikes report back (docs/spikes/STATUS.md).
