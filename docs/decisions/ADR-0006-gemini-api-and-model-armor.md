# ADR-0006: Model access and guardrails: Gemini API, Model Armor + guardrail prompt
- Status: Accepted (seeded from SRS v0.2 Appendix A)
- Date: 2026-11-14
- Requirements: SDD 3.3; Doc 4

## Context
Options were considered during design and replaced; recorded so they are not reintroduced by mistake.
Documented: Vertex AI (Netherlands) replaced by Gemini API; Flash-Lite judge replaced by Model Armor plus guardrail prompt (SRS Appendix A).

Likely reasons (confirm): Model Armor gives purpose-built filters (PI/JB, RAI, URL, sensitive data) without an extra LLM call per turn; lower latency and cost; region asia-south1 is closer.

## Decision
Gemini API (regions per SDD 3.3); Model Armor (asia-south1) plus guardrail prompt and Gemini safety settings.

## Alternatives considered (superseded)
Vertex AI (Netherlands region); Flash-Lite judge for guardrails

## Consequences
Revisit when the related spikes report back (docs/spikes/STATUS.md).
