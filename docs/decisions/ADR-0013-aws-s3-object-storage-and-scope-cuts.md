# ADR-0013: Object storage: AWS S3; v1 complaint/ticket-status agents removed
- Status: Accepted (seeded from SRS v0.2 Appendix A)
- Date: 2026-11-14
- Requirements: SRS Appendix A

## Context
Options were considered during design and replaced; recorded so they are not reintroduced by mistake.
Documented: Neon Object Storage replaced by AWS S3; complaint and ticket-status agents (v1) removed from scope (SRS 2.2, FR-FB-06).

Likely reasons (confirm): S3 is the MVP target storage (SDD 21) so no migration; removing complaints/tickets avoids needing account-specific integrations.

## Decision
AWS S3 for KB docs, clips and recordings. Complaint and ticket-status agents removed from scope.

## Alternatives considered (superseded)
Neon Object Storage; complaint and ticket-status agents (v1)

## Consequences
Revisit when the related spikes report back (docs/spikes/STATUS.md).
