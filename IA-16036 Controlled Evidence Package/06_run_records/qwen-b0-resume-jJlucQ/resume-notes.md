# Explicit resumed B0 experiment

- Parent: `qwen-b0-ClBDGA`; failed at claim review, no V1.
- This run uses a separate consistent SQLite backup and copied local evidence storage. Parent source files, input artifacts and failure records are unchanged.
- Application: `try4.3.1-passage-owned-claim-review`.
- Same incident, model digest and B0-only documents. No new answers, later batch, storyteller, fallback model or evaluator instructions supplied.
- Resume dispatched once at 2026-09-16T19:22:05Z.
- Observed at 19:22:14Z: **36 `model-call-reused` checkpoints**, covering all work before claim review. No new upstream model calls. The two successful old claim-review calls are not reused because the stage prompt/schema changed.
- New inference begins at claim review. Its new requests and raw responses are saved inside model-call checkpoints. This run does not use a transparent HTTP capture proxy.
- Resume stops on the first failed stage or first committed V1. Saved-model reuse is established; successful claim review and a defensible causal board are not yet claimed.

Dashboard: http://127.0.0.1:3004/incident/b7c62bf9-604c-4312-9520-7b63b20b7363

## Observed claim-review completion

At 2026-09-16T19:28:42Z, all 12 new claim-review batches finished on their first provider attempt. The completed stage saved 45 reviewed claims: 26 supported, 9 partially supported and 10 unknown.

A read-only inspection of the saved stage found 61 citations; every source ID resolved to the original incident or a supplied document segment, and every excerpt was an exact substring of that source. This verifies citation identity/text, **not semantic entailment**.

Nine model-proposed supported verdicts had false checks. The application withheld full support for all nine and recorded their checks and downgrade reasons; they became partially supported, not silently verified. This includes the formerly failing unknown-origin claim. The qualifications claim selected the actual personnel passage with all checks true.

The causal stage is now running. No V1 or full RCA success was established at the time of this review. Remaining quality concerns include model inconsistency across similar claims and the unchanged upstream structuring loss. A supported review label still requires substantive inspection: for example, the ECP candidate preserves the OR alternative but omits the source's explicit issuance requirement, which its model reviewer did not flag.
