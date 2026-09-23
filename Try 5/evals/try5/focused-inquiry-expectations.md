# Focused causal inquiry — frozen expectations, 2026-09-19

Keep Qwen's saved digest and original production checkpoint unchanged. No model
ensemble, fallback, training, storyteller, withheld truth, or automatic full run.

## A. Saved-request profile comparison (before code/prompt changes)

Replay `outputs/audited-board-pilot-BiUUCI/04-causal-request.json` with native
thinking and the documented Qwen general-task thinking sampling profile. Preserve
system prompt, evidence packet, schema, model digest, context and output allowance.
This changes a profile, not solely a boolean. Compare with the preserved original
output; do not call a successful API response a reasoning improvement.

Assess whether the output recognizes the selected P-U/P-R contrast, asks a more
discriminating question, preserves sampled-only and unknown mapping limits, and
avoids asserting a particular valve state, compressor failure or root cause.
Also replay the saved `06-verify-request.json`: its documented condition is
supported, but the expanded “system state could be incomplete” wording and old
call-local citations must not receive an unexplained blanket approval.

## B. Engineering changes, independently assessed

- Preserve exact claim identity/scope; separate evidence origin, truth status and
  causal eligibility. A review's changed category must not silently remove a fact
  from causal consideration. Surface the disagreement without rewriting truth.
- Render factual node text from the reviewed assertion. New model prose is a
  proposal, not a second fact smuggled into a supported node.
- Resolve source aliases to durable document/span provenance at ingestion. Never
  carry S1/F1 aliases into another model call as if globally meaningful. Preserve
  raw outputs separately. Original source text must not be modified.
- A focused inquiry considers related evidence and alternative explanations,
  with discriminating requests. It does not require a predetermined cause or
  promote its hypotheses into supported facts/edges.
- Existing broker/answer routing and per-model isolation remain intact.

## C. Live focused-inquiry comparison

Use the same saved three-claim neighborhood and original B0 + IA-P01 sources.
Assign a generic evidence-change / explanation-comparison objective, without
injecting the expected pressure contrast into the prompt. The model must identify
it from the supplied documents. No other progressive document is supplied.

Expected useful result: identify what the selected readings establish, retain
uncertainty about physical mechanism and sensor/topology assumptions, and request
evidence that distinguishes plausible explanations. Preserve known observations.
Questions should explain how different answers would change the investigation.
Allow no causal conclusion if the evidence is insufficient. Require substantive
progress, not just no hallucination. Do not hardcode IA identifiers in production.

These diagnostics are not app versions, complete RCA, or passage of the existing
24-case claim-review gate. The previous compound-claim failures remain part of
acceptance; category/provenance improvements alone do not solve entailment.
