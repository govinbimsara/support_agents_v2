# Spike status (SDD v0.3 section 20)
Update after each spike. Result = PASS / FAIL (fallback chosen) / NOT RUN. Link the evidence (PR, trace, note).
Run spikes before feature build-out. Suggested first: 1, 2, 11 (they unblock everything else).

| # | Verify | Pass criterion | Fallback | Result | Evidence / chosen fallback |
|---|---|---|---|---|---|
| 1 | ADK 2.13 DatabaseSessionService on Neon (pooled + NullPool) | Health check passes; concurrent sessions without driver errors | Tune pool; direct endpoint | NOT RUN | |
| 2 | LiveKitRunner on LiveKit Cloud ap-south; Mumbai -> Neon latency | Call connects; DB round-trip measured | Worker on Railway Singapore (force IPv4 for WebRTC or enable outbound IPv6) | NOT RUN | |
| 3 | Barge-in; Silero; heard-only transcript | NFR-PRF-04 met | Custom buffer clear; transcript truncation | NOT RUN | |
| 4 | AgentTool (text model) in run_live; filler before tools | Works; NFR-PRF-02 met | Function tool wrapping run_async | NOT RUN | |
| 5 | Graph RequestInput when invoked from run_live | Pause/resume across turns | flow_step function tool | NOT RUN | |
| 6 | Post-call routing to Supervisor; voice transfer_to_agent | First chat message handled by Supervisor | post_call check in specialists | NOT RUN | |
| 7 | Language hold on Live; mid-call change | Replies stay in stored language | Reconnect with new instruction | NOT RUN | |
| 8 | Resumption with full prompt; 20-min call | No re-greet; state kept | History replay | NOT RUN | |
| 9 | Model Armor asia-south1 filters, latency, SI/TA detection | Filters active; latency recorded | Different region (e.g. europe-west4) | NOT RUN | |
| 10 | Live speaks exact refusal; clip on agent track; reset | Refusal heard; attack absent after reset | Clip mode; second track | NOT RUN | |
| 11 | Langfuse with GenAI v2 spans | Traces readable | Legacy span format setting | NOT RUN | |
| 12 | Recording enabled to test bucket | File in S3; uri stored | Worker-side upload | NOT RUN | |
| 13 | DTLN vs LiveKit noise cancellation; iOS/Android mic | False interruptions <= target | Browser noiseSuppression | NOT RUN | |
| 14 | Model failover | Failover on simulated error | Manual config switch | NOT RUN | |
| 15 | LiveKit Cloud free plan: self-built agent warm vs cold start on dispatch | Call start time within NFR-PRF targets | Paid plan (MVP-05) or worker on Railway | NOT RUN | |
| 16 | Clip generation verbatim with Live | Transcript matches | Gemini TTS | NOT RUN | |
| 17 | Flow step re-run on workflow resume (FR-TS-07) | No duplicate transitions or 'tried' entries | flow_step function tool with explicit idempotency key | NOT RUN | |
