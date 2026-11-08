# V2 upgrade: what the tests genuinely establish

These are **controlled software interventions**, NOT results of a fresh language model. Test code deliberately fixes input evidence/proposals so each method's contribution can be isolated. All claims about machine or accident reality still require source evidence and expert review.

| Condition varied (same controlled inputs) | Observed V2 behavior | Test path |
|---|---|---|
| Two hypotheses require different conditions yet share the same accident outcome terms. | Hypothesis matrix leaves the unmatched condition unresolved; does not count generic event-word overlap as a discriminator. | `tests/methods/test_real_v2_algorithms.py::test_hypothesis_matrix_exposes_unquestioned_conditions_not_causes` |
| A plausible route serves three unresolved gaps instead of one. | One-step Lead's displayed route-access/coverage score increases, without predicting documents or outcomes. | `test_lead_coverage_method_values_shared_route_without_future_answer_oracle` |
| Same question, varying declared request burden. | More costly action receives a lower score; an exhausted `(gap, route)` action is rejected by admissibility. | `test_lead_cost_penalty_and_retry_guard_are_effective` |
| An available custodian has already returned partial evidence on the same question. | Route map removes the exhausted pair and does not reveal hidden document IDs or another custodian's inventory. | `test_route_map_excludes_exhausted_route_and_never_adds_private_file_ids` |
| Later bench result is incorrectly proposed as an incident-time measurement. | Conservative Assessor preflight quarantines the mismatched *assertion*. The same reading correctly scoped as post-incident remains admissible. | `test_assessor_scope_guard_flags_incident_time_bench_test_and_not_generic_warrant`, `test_scoped_post_event_distinctions.py` |
| The quarantined assertion had been used to mark an information need as covered. | That gap resolution is suppressed, the independent report claim survives, the original raw source can still be admitted. | `test_assessor_scope_quarantine_keeps_unrelated_claim_and_open_gap` |
| Model emits valid JSON containing a fake current-document quotation. | Contract rejects it, sends only a bounded format error for one retry, then accepts only actual quotation from the supplied source. | `test_structural_retry_repairs_without_answer_oracle`, `test_quote_that_is_not_in_source_is_rejected` |
| Five-agent prompt-only comparator versus V2 modules/prompts. | All configurations execute on fresh environments. Prompts and implementations can be switched independently, the ledger preserves the fixture's six source/correction invariants. | `tests/evaluation/test_matrix_and_prompts.py` |
| Real provider endpoint is not configured. | Execution records failure; it **does not create model responses from the authored fixture**. | `test_preflight_failed_live_mode_never_records_fake_inference` |
| Initial report only; future documents still hidden. | Saved first model inputs contain only released record and public state, never future synthetic document identifiers. | `tests/evaluation/test_model_payload_receipts.py` |

## Metrics from the saved four-way authored fixture comparison

| Profile | Model-interface calls | Actual provider completions | Sources released | Corrections applied | Authored invariants | Expert review |
|---|---:|---:|---:|---:|---:|---|
| V1 prompt-only | 35 | 0 | 6 | 1 | 6/6 | Not performed |
| V2 prompts-only | 35 | 0 | 6 | 1 | 6/6 | Not performed |
| V2 methods-only | 33 | 0 | 6 | 1 | 6/6 | Not performed |
| V2 full | 33 | 0 | 6 | 1 | 6/6 | Not performed |

**Do not interpret 6/6 as model accuracy.** The six checks are author-authored expectations on ONE synthetic case, scored on author-authored model responses. In particular, because the fixture ignores prompts entirely, the 35-call V1 versus 35-call prompts-only run **cannot measure** a prompting technique's effect on an actual model. Model-interface calls are not network LLM calls. The method-only difference is software behavior, not scientific causal improvement.

## Remaining model evaluation dependency

The experimental design and reviewer sheets are implemented, but there are **zero remote LLM completions in this build**. A network-enabled environment with an API secret, independent investigator, held-out industrial cases and domain expert must complete the final validation phase. V3 algorithm design can be done independently, provided the paper does not misrepresent V2 as already independently validated.
