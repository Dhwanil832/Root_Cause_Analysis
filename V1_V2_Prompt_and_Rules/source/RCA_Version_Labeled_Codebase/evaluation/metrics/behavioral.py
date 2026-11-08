"""Public operational measures and developer-only fixture invariants.

This is NOT causal accuracy or human expert evaluation. A reference manifest
is loaded only from evaluation/private_reference by the *offline scorer*, never
placed into an investigator request or public context.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path


def inspect_run(root,reference=None):
    root=Path(root)
    summary=json.loads((root/'summary.json').read_text())
    trace=json.loads((root/'trace.json').read_text())
    model_calls=json.loads((root/'model_calls.json').read_text())
    original=[e for e in trace if e.get('event')=='source_assessed']
    steps=[e for e in trace if e.get('event')=='decision_selected']
    provider_http=sum(bool(c.get('actual_call_performed')) for c in model_calls)
    calls=Counter(c.get('task','unknown') for c in model_calls)
    labels={x.get('semantic_label'):x for x in summary.get('claims',[])}
    gaps={g.get('semantic_label'):g for g in summary.get('gaps',[])}
    attempts=[e for e in trace if e.get('event')=='evidence_requested']
    actions=[]
    for e in steps:
        a=e.get('selected_action') or {}
        if a.get('mode')!='wait':
            actions.append({'gap_id':a.get('gap_id'),'route':a.get('route'),'mode':a.get('mode')})
    duplicated_action_pairs=len(actions)-len({(a['gap_id'],a['route'],a['mode']) for a in actions})
    result={
        'case':summary.get('case'),'mode':summary.get('mode'),
        'model_provider':summary.get('llm_provider'),
        'provider_http_completions':provider_http,
        'provider_http_attempts':summary.get('provider_http_attempts',0),
        'input_tokens_reported':sum(int((c.get('tokens') or {}).get('prompt_tokens', (c.get('tokens') or {}).get('input_tokens',0)) or 0) for c in model_calls),
        'output_tokens_reported':sum(int((c.get('tokens') or {}).get('completion_tokens', (c.get('tokens') or {}).get('output_tokens',0)) or 0) for c in model_calls),
        'claims_of_independent_model_quality':False,
        'model_completions_by_task':dict(calls),
        'total_model_interface_completions':len(model_calls),
        'rejected_model_response_contracts':len(summary.get('contract_rejections',[])),
        'sources_received_count':len(summary.get('sources_assessed',[])),
        'source_assessments':len(original),
        'dispatched_requests':len(attempts),
        'request_outcomes':dict(Counter(x.get('returned','unknown') for x in attempts)),
        'action_decisions':len(steps),
        'repeated_action_tuples':duplicated_action_pairs,
        'unresolved_information_needs':sum(g.get('status')=='open' for g in gaps.values()),
        'candidate_hypotheses':len(summary.get('hypotheses',[])),
        'causal_links':len(summary.get('causal_view',{}).get('links',[])),
        'correction_events':len(summary.get('corrections',[])),
        'signed_off':bool(summary.get('signed_off')),
        'stop_reason':summary.get('stop_reason'),
        'prompt_sha256':summary.get('prompt_hashes',{}),
        'policy_config':summary.get('component_config',{}),
        'prompt_variants':summary.get('prompt_variants',{}),
        'review_status':'No independent industrial expert review conducted',
    }
    if reference is not None:
        oracle=json.loads(Path(reference).read_text())
        checks={}
        delivered=set(summary.get('sources_assessed',[]))
        checks['authored_records_released']=set(oracle['required_delivered_source_ids']).issubset(delivered)
        for label in oracle['must_remain_supported']:
            checks['preserved_'+label]=labels.get(label,{}).get('status')=='supported'
        for label in oracle['must_not_remain_supported_after_correction']:
            checks['withdrew_'+label]=labels.get(label,{}).get('status')!='supported'
        for label in oracle['must_remain_open']:
            checks['unresolved_'+label]=gaps.get(label,{}).get('status')=='open'
        if oracle.get('must_not_sign_off'):
            checks['no_premature_sign_off']=not summary.get('signed_off')
        result['authored_fixture_invariants']={
            'passes':sum(checks.values()),'count':len(checks),'checks':checks,
            'warning':'Author-designed expected states on ONE synthetic incident; not independent causal correctness or model skill.',
        }
    return result
