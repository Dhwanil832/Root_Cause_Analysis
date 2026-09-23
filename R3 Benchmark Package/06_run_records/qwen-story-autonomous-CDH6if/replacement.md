# Verification-reference repair and replacement

The parent remains stopped with an uncommitted causal draft and zero versions. No version was manufactured, no response was rewritten, and no previous incident was resumed.

Repair version: `try4.2.2-verification-contract`. The new stage-specific output schema enumerates actual board node/edge IDs and restricts verified edge indexes to valid integers; edgeless boards allow only an empty verified-edge array. The prompt treats IDs as opaque and forbids changing prefixes. Runtime validation and blocking-finding precedence remain intact. Successful verification checkpoints now preserve raw output/attempts alongside the mapped board.

Verification before replacement:

- All 38 regression tests passed, including the two exact invented-ID outputs, bounded same-stage repair, refusal to normalize bad prefixes, and honest empty/edgeless results.
- Type checking, lint and production build passed.
- Focused live Qwen check `../qwen-verification-contract-iCfSSk/` used the exact saved draft and evidence reconstructed from its saved first-cycle checkpoints. It completed in one attempt in 70 seconds, with eight findings/questions, one verified node and zero verified edges. This checks reference integrity, not truth of every judgment or completion of a full RCA.
- Original snapshot SHA-256 remained `2ed8406beaad1055242e8bbc0d35b6b2db7265a006e924c517f3d098b078dca3`.

Schema references: [Structured Outputs constraints](https://developers.openai.com/api/docs/guides/structured-outputs). Compatibility was checked with local Qwen, not inferred from OpenAI documentation alone.

Fresh replacement launched 2026-09-15T15:33:42Z:

- Run: `../qwen-story-autonomous-pTsSr7/`
- Incident: `f6388578-8905-44cb-a66e-75c06a2a21d5`
- Track: `6e6a6dcd-e460-452f-a738-a7b640cefcce`
- Dashboard: http://localhost:3000/incident/f6388578-8905-44cb-a66e-75c06a2a21d5
- Model: unchanged `ollama:qwen3.5:latest` in both roles.

The existing monitor now targets that replacement at two-hour intervals. This is the only replacement launched during this repair check. A repeated previously repaired reference-contract failure must trigger diagnosis/reporting and a pause, not an indefinite restart loop.
