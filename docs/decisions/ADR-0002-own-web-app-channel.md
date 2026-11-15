# ADR-0002: POC channel: own web app; WhatsApp at MVP
- Status: Accepted (seeded from SRS v0.2 Appendix A)
- Date: 2026-11-14
- Requirements: SRS MVP-01; SDD 4

## Context
Options were considered during design and replaced; recorded so they are not reintroduced by mistake.
Documented: WhatsApp calling needs Meta verification; test numbers are rarely issued in this region; the calling sandbox is for Tech Partners only; unofficial libraries are against WhatsApp terms with ban risk and no calling (SRS Appendix A, MVP-01).

Likely reasons (confirm): a web app lets chat and voice be tested end to end with no third-party approvals; the channel adapter contract (SDD 4.1) keeps WhatsApp addable later.

## Decision
Own web app for the POC. Official WhatsApp Cloud API and Calling API at MVP (MVP-01).

## Alternatives considered (superseded)
n8n; WhatsApp; Telegram (bot + Mini App); WhatsApp simulator; Twilio BSP; Meta test number; Meta calling sandbox; unofficial libraries (Baileys, whatsapp-web.js, Evolution API, WAHA); Facebook Messenger Business Calling

## Consequences
Revisit when the related spikes report back (docs/spikes/STATUS.md).
