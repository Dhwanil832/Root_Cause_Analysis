# Broker failure during the first storyteller update

The scheduled inspection confirmed one committed version (V1), not four. V1 completed at 2026-09-15T04:33:56Z. Qwen then generated a validated batch of 16 storyteller answers, released at 04:36:54Z. The V2 update reached the broker after understanding, structuring, tagging, adjudication and six specialist checkpoints, then stopped at 04:49:10Z. The experiment runner and its mutation request had exited before repair; no processes were killed and no failed mutation was retried.

Failure checkpoint: `e0a0dbc1-4ea2-4b48-a586-4c53ddbef732`, target version 2, stage `question-broker`, run `83788998-a50c-4e81-9c5d-ff71ed408364`. Both raw attempts remain in `latest-incident.json` and the app checkpoint. No broker batches were accepted during this update.

The four candidates were already answered baseline questions: `bq-hhq8mg`, `bq-ws1sje`, `bq-1oj29hu`, and `bq-gifup5`. Attempt 1 marked all four covered by themselves, contrary to the existing identity/coverage rules. Attempt 2 changed each disposition to keep but retained the self-owner ID. The runtime rejected both outputs and correctly prevented an incomplete V2 from being committed.

Confirmed harness defect: the decoding schema independently enumerated dispositions and owner IDs, permitting combinations forbidden by the application contract. Answered-candidate and owner-eligibility restrictions existed only in prose/runtime checks. Repair will encode those existing constraints as per-candidate schema alternatives while retaining runtime validation, original question identities, evidence and bounded retries. This does not establish that the model's merging judgments or RCA conclusions are sound.

Before repair, affected production files matched the experiment's frozen hashes. Original artifact SHA-256 values:

- `latest-incident.json`: `1012683288dea001e4576028f02f85a99cf551d79f1ce14102643a05ddad83be`
- `version-1.json`: `e62a74b3059b8f2ada8ee459d91da9f69231f8fba49641d39fb1d14d7d35c781`

The original run, story batch, evidence and version are preserved. Any replacement must be a new incident and run directory after regression verification, never a rewrite or resumption of this failed update.
