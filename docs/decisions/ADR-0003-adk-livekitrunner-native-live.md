# ADR-0003: Voice: ADK LiveKitRunner with native Gemini Live speech-to-speech
- Status: Accepted (seeded from SRS v0.2 Appendix A)
- Date: 2026-11-14
- Requirements: SDD 3, 20

## Context
Options were considered during design and replaced; recorded so they are not reintroduced by mistake.
Documented: Pipecat/pipecat-adk and cascaded STT -> ADK -> TTS were replaced (SRS Appendix A).

Likely reasons (confirm): native speech-to-speech removes STT/TTS hops and latency; ADK LiveKitRunner keeps one agent framework for chat and voice, sharing sessions, tools and tracing; client-side noise suppression avoids server-side RNNoise cost.

## Decision
ADK LiveKitRunner; native Gemini Live speech-to-speech; client-side noise suppression (spike 13).

## Alternatives considered (superseded)
Pipecat, pipecat-adk, server-side RNNoise; cascaded STT -> ADK -> TTS

## Consequences
Revisit when the related spikes report back (docs/spikes/STATUS.md).
