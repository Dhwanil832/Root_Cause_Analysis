# Frozen incident story — evaluator only, never upload

Frozen before incident creation on 2026-09-09. Scope: replay the historical R3 carrier-beam incident through existing Try 4 API using only `ollama:qwen3.5:latest`. This is the persistent separate Incident Story Agent. Source inventory hashes are recorded in evidence-inventory.json before creation. No application code, prompts, defaults, settings, existing incidents, or manual cause approvals may be changed. No previous model outputs are case evidence.

## Historical narrative and accepted reported findings

The focal event is the October 14, 2024 approximately 1:03 PM fall of the R3 delivery/exit carrier beam from its yoke into the pit onto sled/scaffold. Contractors occupied the pit earlier but none was in it at the fall; two nearby contractors witnessed it. Beam/link intact, keeper installed, no apparent gross yoke damage, small top-operator-side liner fell too. No relevant crane lift reported. Rolls had been removed; top balance left raised; B hydraulics shut down, isolated and bled.

Partner-reported findings, available only progressively via controlled derivatives: absent backup rolls allowed travel beyond the usual installed-roll limit; beam wedged against top mill spreader and posts; yoke drifted downward over approximately two hours while beam remained wedged; relative motion moved link off center until its stop cleared yoke/lifting point. The isolation valve was reported/believed to slowly bleed through, capable of permitting drift. Original arrangement had one keeper per link arm and no stop preventing roll-removed interference. Keeper presence did not prevent the displaced release path. Gravity/stored energy not fully accounted for and adequate independent positive mechanical restraint not established. Beam approximately 8,500 lb. Reported wear measurements were insufficient for ordinary seated release. Valve inspection reportedly reactive rather than routine. These are accepted investigation findings summarized by partner sources, not independently reproduced raw forensic proof.

## Fixed limitations

No raw leak-down rate/bench test/pressure historian, calibrated time-displacement trace, full original video/annotations, raw dimensions or tolerance stack, force reconstruction, signed complete LOTO execution/turnover package, original field photographs, authorization identifying who left balance raised, proof of whether a temporary restraint was installed then removed, prior valve-defect history, or causal role of liner is supplied. Exact first-wedging time and configuration-specific stand-wide modification applicability unavailable. Never fabricate these. Return “Not established by the available benchmark evidence” with missing record. Preserve “reported,” “believed,” “approximately,” and missing-source limitations.

Partner chart’s A-hydraulics entry conflicts with B narrative; not a blind-model finding unless an underlying released source establishes it. Revision-0 incomplete action checks and later presentation completion reports have different times/revisions. Do not infer new historical facts from general knowledge or internet.

## Synthetic completion and source classes

Original synthetic PDFs add controlled scenario detail: local zero-gauge time/reading and missing signatures, specific synthetic ECP requirements, keeper pin/open-pocket conceptual geometry, scene indexes, attributed witness accounts, partial video timestamps, crane controller log, occupancy times, qualifications, similar-stand visual findings. These are synthetic scenario facts, explicitly not authentic company measurements or records. Blank fields show documentation gaps, not physical absence. Original synthetic short video view is distinct from later partner-reported extended review; it cannot establish upper-interface motion.

GTDE markdown are controlled benchmark derivatives of partner findings, not company records. Derivatives/excerpts must keep source label, basis, qualifiers and limitations; omit unrelated facts and corrective-action hints. Do not release withheld map, expected findings, answer bank, rubric, this freeze, full causal solution, prior outputs, or partner RCA originals.

## Frozen release policy

1. Phase0: exact original description, exactly three starter PDFs, existing defaults cloned by app unchanged. Persist their identities, hashes, revisions first.
2. Read actual baseline, canonical and verification questions and answer-fetch results. Log canonical owner, proposedBy, shared routes, merged/skipped relationships.
3. Narrow matching original synthetic record first. Targeted answer + source ID/class/limit. Release GTDE only when an actual remaining question/gap requires it after that original level. No adjacent truth-chain dumping.
4. After the model has an initial evidence base, release the existing three challenge PDFs together at the next relevant version. Do not warn which are misleading; metadata supplies cues. Do not create new misleading company records.
5. Reuse consistent prior answers for duplicates; don't manufacture evidence for blocked questions. Continue while an actual question has new useful releasable evidence or clarification. Stop only on supported/blocked chain, alternatives bounded, actions produced or correctly withheld and no material value from another version, or evidenced repeated no-progress/evidence exhaustion.
6. Existing /api/uploads then /api/tracks/{id}/versions only. One running version at a time. Long-lived curl. If request disconnects inspect async checkpoints/versions before any retry. Log all errors/interventions; never silently lower a gate or manually approve a cause.

The parent independently evaluates, owns services, and receives proposed-release rationale before submission. Routine releases within this policy were preauthorized by parent; new-fact conflicts require consultation.
