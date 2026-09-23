# Focused claim-review check — expectations written before inference

Run: `da57d29d-cf54-4c29-85ae-54260ef92dcd`, generation 49, still paused.
Producer: `a2cf610c9ef219431573e9e8fc1d77eb09978ab4ae890f3930ba7bc69939dcb9`.
Five saved findings from the recovered equipment specialist; same Qwen digest,
same released B0 documents, same production review prompt/schema/executor.

This is an isolated diagnostic, not a new incident revision or a claim that the
full pipeline has reached review. The application DB stays read-only. Each review
sees its one original finding and normally retrieved source passages; it never
sees this file, other diagnostic verdicts, hidden answers or extra evidence.
Production review application is exercised on independent in-memory state copies.

## What should happen

1. `87878641-6e06-4003-b0d0-bd00ca271e73`: do not fully support “no temporary
   instruction attachment is present.” The cover establishes a blank field;
   conventions say its reason needs other evidence. Preserve revised-and-issued
   ECP OR approved temporary-instruction alternative, and the applicability
   condition for a service-routing change. A hypothetical documentation gap is
   not an established missing barrier. Partial/unknown is appropriate; explicit
   physical absence is not proved. A contradiction with the convention is not
   itself evidence the attachment actually existed.
2. `91ee1a25-2724-442f-a931-cd7b2132a696`: distinguish what §5.1 requires the
   package to record from a claim that work records exclude valve/pressure data.
   A limited cover excerpt cannot prove that the execution record has no such
   data. Partial support or explicit narrowed scope, not unconditional support
   for the whole bundled requirement. General record requirements are context
   or requirements, not evidence of an incident mechanism.
3. `d6d606d9-c87c-412c-9f0e-ba3d0d6579a6`: preparation-only stage is supported
   by the actual cover/log, not merely by a directory explaining general roles.
   Require source support specific to this job/stage; the reviewer can correct
   support by citing those original sources. Do not infer actual valve positions.
4. `1e43077f-8ff5-46b7-80bc-455e36de71c0`: support the recorded WO-527-E blank
   status **at folder issue**. This is not proof no later work was performed or
   that physical isolation was missing. Route simple record metadata as context.
5. `96627800-22e2-48d2-ac6f-f4200d33eea4`: support the recorded revision/blank
   field, preserving issue-time scope. Do not infer the revision was outdated,
   the temporary document was required or the absence caused the incident.

Novelty is a separate failed specialist behavior already recorded in the recovery
receipt. This reviewer is not a cross-finding duplicate broker and does not see
the whole notebook. Do not award it duplicate-detection credit it cannot earn.

Pass criteria: valid target-specific responses, source-grounded verdicts, the
missing-document overclaim caught, supported record observations retained, and no
administrative metadata promoted into established physical causes. Record raw and
effective verdicts separately: application handling can differ from model output.
