# ADR-0008: Language is per conversation, changed only via set_language
- Status: Accepted (seeded from SRS v0.2 Appendix A)
- Date: 2026-11-14
- Requirements: FR-LANG; SDD 5.3

## Context
Options were considered during design and replaced; recorded so they are not reintroduced by mistake.
Documented: replaces per-user language; language changes only via set_language, never detected per message (FR-LANG-01..03, v1 per-message detection removed in SDD 6.4).

Likely reasons (confirm): per-message detection flipped languages on romanized/mixed input, which is common among Sri Lankan users.

## Decision
Language stored per conversation; changes only through the set_language tool; never detected per message.

## Alternatives considered (superseded)
user:language (per user)

## Consequences
Revisit when the related spikes report back (docs/spikes/STATUS.md).
