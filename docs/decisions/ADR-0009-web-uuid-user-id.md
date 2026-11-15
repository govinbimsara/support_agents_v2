# ADR-0009: Identity: user_id = web:<uuid>, no linking in POC
- Status: Accepted (seeded from SRS v0.2 Appendix A)
- Date: 2026-11-14
- Requirements: SDD 4.1, 21

## Context
Options were considered during design and replaced; recorded so they are not reintroduced by mistake.
Documented: no identity table, merchant ID or test-merchant switch in the POC; account-specific data is out of scope (SRS 2.2).

Consequence: strikes and sessions are per browser identity; clearing storage resets them (SDD 11 known limitation; MVP-09 rate limiting).

## Decision
user_id = web:<uuid>; no identity linking in the POC. Verified identity at MVP.

## Alternatives considered (superseded)
Identity table; merchant ID field; test-merchant switch

## Consequences
Revisit when the related spikes report back (docs/spikes/STATUS.md).
