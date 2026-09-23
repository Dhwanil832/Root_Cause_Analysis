# Preserved failure and verified replacement

This run remains failed with one committed V1. It was not resumed, overwritten, or padded with an incomplete V2.

Repair: `try4.2.1-broker-contract` encodes the existing broker rules as legal per-candidate schema alternatives. A keep decision can only have an empty owner field; a covered decision cannot target itself or a future candidate; answered candidates can only be kept. Runtime completeness/owner checks remain intact. The broker prompt now explains that keeping an answered question preserves its answer link rather than asking it again.

Verification before replacement:

- All 35 regression tests passed, including both exact failed outputs, same-stage repair, and answer-identity preservation.
- Type checking, lint, and the production build passed.
- A focused real Qwen check replayed the four failed answered questions plus four saved specialist follow-ups. It completed two batches on the first attempt each in 70.6 seconds, retaining four and marking four covered. It did not create an incident or commit a version. Artifacts: `../qwen-broker-answer-contract-rquoTW/`.
- The original saved snapshot and V1 hashes remain unchanged. No existing model output or source evidence was edited.

The schema change follows [nested schema-alternative guidance](https://developers.openai.com/api/docs/guides/structured-outputs) and the [Ollama structured-output interface](https://docs.ollama.com/capabilities/structured-outputs); local live validation, not OpenAI compatibility alone, was used to check this Qwen execution path.

Fresh replacement launched at 2026-09-15T12:37:16Z:

- Run: `../qwen-story-autonomous-CDH6if/`
- Incident: `bbcb9721-c1ac-4430-90a3-154ea2eca033`
- Track: `5be64286-f121-4e05-9620-4085671563cb`
- Dashboard: http://localhost:3000/incident/bbcb9721-c1ac-4430-90a3-154ea2eca033
- Model: unchanged `ollama:qwen3.5:latest` in both roles.

The existing two-hour monitor now targets that replacement. No duplicate monitor was created. The fix addresses an execution-contract gap, not proof of sound merging decisions or a correct root cause; the replacement still has to produce and validate four causal versions.
