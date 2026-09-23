# Verification target-ID failure

The two-hour follow-up found this run stopped with zero committed versions. Broker, answer fetching, evidence processing and causal analysis completed. The causal draft has 11 nodes and seven edges. Verification failed after two attempts at 2026-09-15T12:58:06Z, so no V1 was committed and no storyteller round began. The experiment process and initialization request had exited before repair; no processes were killed or mutations repeated.

Failed checkpoint: `0229bc73-6503-43fd-84ec-94fd78dd0045`, target V1, run `d337b107-ad4c-4542-9173-8b701b20b2f4`. The exact raw attempts and original draft remain in `latest-incident.json` and the app checkpoints.

- Attempt 1 invented finding target `edge-iqm0nn`; the board contains `node-iqm0nn`, not that edge.
- Attempt 2 invented `edge-1qd881d`; the board contains `node-1qd881d`, while its outgoing edge has the distinct ID `edge-11tbp77`.

No board finding supplied these invalid IDs: Qwen substituted an edge prefix onto node IDs. Runtime validation correctly rejected both attempts. The decoding schema still accepted arbitrary strings for finding targets and verified nodes, permitting invalid identifiers despite the application having the exact legal set. This is a different stage-specific contract gap from the answered-question broker failure; the previous broker fix was not reverted or bypassed.

Repair scope: bind verification output IDs and edge indexes to the supplied board during decoding, keep runtime reference validation and blocking-finding precedence, and explicitly instruct the verifier to copy opaque IDs without changing prefixes. Never silently rewrite an invalid model ID or manufacture an edge to make the output pass. Evidence, causal claims, node statuses and the frozen historical draft remain untouched.

Before repair, affected source/prompt files matched the frozen hashes. Original `latest-incident.json` SHA-256: `2ed8406beaad1055242e8bbc0d35b6b2db7265a006e924c517f3d098b078dca3`.

This run has execution failure and an uncommitted draft, not a completed RCA or a valid new performance score. A fresh replacement is authorized only after regression and focused live verification of the fix.
