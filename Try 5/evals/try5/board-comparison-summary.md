# Controlled Qwen board comparison — 19 September 2026

**Result: the bounded run completed, but the investigation-quality result is
partial. No full RCA acceptance or root cause is claimed.**

## What actually changed

| Item | Baseline, after node-verification correction | After one pressure/alarm document |
| --- | --- | --- |
| Air-low indication | Supported from incident account and shift log | Still supported; alarm row also cited, without its input mapping |
| Return to normal band | Supported actual-state observation | Still supported; P-R recovery values used, but reclassified as record-only context |
| Preparation-only work boundary | Supported condition, causal role unproved | Same node ID and title; supported, but its expanded detail contains loose wording |
| Causal connections | None | None |
| Useful investigation progress | Requests evidence of interruption mechanism and crew actions | Mostly overlapping questions; little use of P-U/P-R contrast |

One condition plus the focal incident is an initial investigation map, not a
causal explanation. The pressure record was available to every new call. This
pilot reconsidered three existing findings, rather than extracting every new
pressure-table row into its own finding.

## Concrete changes retained in the code

- A rejected review can preserve its proposed evidence-gap question without
  turning the rejected claim into a fact or blocking unrelated work. Verified
  with deterministic tests and replay of an actual failed model response.
- A node verifier now checks whether the stated event/condition is established;
  a separate relationship verifier checks whether a causal connection is
  established. The corrected node behavior passed a real-Qwen retest and held
  for the main preparation condition in the controlled comparison.

43 deterministic tests, type checking, lint and build passed. These checks do not
establish that Qwen can perform complete RCA. No real causal links were proposed,
so real-model relationship verification remains untested.

## What still failed quality review

1. The same recovery claim changed category, changing whether it could proceed to
   causal analysis even though the new evidence strengthened it.
2. The node's expanded prose conflates incomplete knowledge of an event sequence
   with “system state could be incomplete”; the verifier did not address that
   distinction in its approval.
3. S1/S2-style labels were retained in prose even when those labels referred to
   different documents in the next call. Structured evidence IDs survive, but
   the prose references are unsafe to read as stable citations.
4. New pressure data improved factual corroboration more than the questions used
   to investigate the cause. The original compound-claim review failures also
   remain unresolved.

## Inspect the preserved outputs

- [Full audit](review-gap-board-results.md)
- [Corrected baseline snapshot](../../outputs/audited-board-pilot-wpypKU/snapshot.json)
- [Controlled-document snapshot](../../outputs/audited-board-pilot-BiUUCI/snapshot.json)
- [Raw comparison summary](../../outputs/audited-board-pilot-BiUUCI/summary.json)

The diagnostic snapshots are not app versions. The original investigation remains
paused at generation 49 with unchanged input/state/snapshot hashes. No storyteller,
hidden evidence, model fallback, retry or full investigation was launched.
