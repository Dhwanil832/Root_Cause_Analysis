# Fresh Qwen experiment: startup check

- Launched: 2026-09-15 04:09:48 UTC (September 14, 11:09 PM America/Chicago).
- Observed until: 2026-09-15 04:13:38 UTC, approximately four minutes.
- Incident: `30502f9f-eaba-42f9-bee8-15324153496e`.
- Track: `5effca62-8b57-4353-ad96-830d2ee5dbab`.
- Model: `ollama:qwen3.5:latest`, unchanged digest `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.
- Frozen prompt version: `try4.2.0-stage-recovery`; frozen source includes the final verification-ID mapping fix.

The app reported completed document-intelligence (04:09:49), incident-understanding (04:11:21), and incident-structuring (04:12:51) checkpoints. No failure checkpoint was present at the final read. Zero versions were committed yet; initial V1 was still processing. The runner and its specific caffeinate companion were active, and the heartbeat updated at 04:13:33. No source, prompt, evidence, or answer changes were made during startup observation.

Existing heartbeat `monitor-qwen-rca-test` was updated through the app to ACTIVE with a 120-minute interval, targeting this exact run. Its first follow-up is intended for approximately two hours after launch. It may repair confirmed execution defects and launch a fresh replacement after verification, but must preserve this run and all prior history, avoid duplicate/uncertain mutations, retain Qwen and the locked evidence world, and stop rather than fabricate progress. Healthy incomplete work continues undisturbed. On four committed versions it analyzes and scores the outputs, reports, and pauses itself.

Dashboard: http://localhost:3000/incident/30502f9f-eaba-42f9-bee8-15324153496e
