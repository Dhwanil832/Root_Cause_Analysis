"""Contract for a *second* LLM's scoped critique of specialist proposals.

The reviewer cannot add facts, source corrections, evidence coverage or causal
edges. It can quarantine specific inference/hypothesis proposals before commit
and raise auditable warnings. Semantic assessments are not engineering proof.
"""
from __future__ import annotations
from copy import deepcopy
from shared.validation import ProposalError, required_quote, bounded_str


def apply_review(source, frontier, result, new_claims=()):
    if not isinstance(result, dict):
        raise ProposalError('Assessor review must return a JSON object')
    allowed={'exclude_inference_indices','exclude_hypothesis_summaries',
             'exclude_assertion_labels','flags','reason'}
    if set(result)-allowed:
        raise ProposalError('Assessor review contains unsupported mutation fields')
    excluded=result.get('exclude_inference_indices',[])
    blocked_assertions=result.get('exclude_assertion_labels',[])
    summaries=result.get('exclude_hypothesis_summaries',[])
    flags=result.get('flags',[])
    if (not isinstance(excluded,list) or not isinstance(blocked_assertions,list)
            or not isinstance(summaries,list)
            or not isinstance(flags,list) or len(excluded)>20
            or len(blocked_assertions)>20 or len(summaries)>20 or len(flags)>12):
        raise ProposalError('Assessor review list invalid or too long')
    proposals=frontier.get('inferences',[])
    hypotheses=frontier.get('hypotheses',[])
    if not isinstance(proposals,list) or not isinstance(hypotheses,list):
        raise ProposalError('Bad specialist proposal shape')
    known_claim_labels={c.get('semantic_label') for c in new_claims}
    if any(not isinstance(label,str) or label not in known_claim_labels for label in blocked_assertions):
        raise ProposalError('Assessor referred to a nonexistent assertion label')
    if any(type(i) is not int or i<0 or i>=len(proposals) for i in excluded):
        raise ProposalError('Assessor referred to a nonexistent inference index')
    all_summaries={h.get('summary') for h in hypotheses if isinstance(h,dict)}
    if any(not isinstance(s,str) or s not in all_summaries for s in summaries):
        raise ProposalError('Assessor referred to a nonexistent hypothesis')
    seen=set()
    validated_flags=[]
    for flag in flags:
        if not isinstance(flag,dict) or flag.get('kind') not in {'scope','entailment','provenance','inference','contradiction'}:
            raise ProposalError('Unknown assessor flag type')
        quote=required_quote(flag.get('quote'),source['text'])
        reason=bounded_str(flag.get('reason'),500)
        key=(flag['kind'],quote,reason)
        if key not in seen:
            seen.add(key)
            validated_flags.append({'kind':flag['kind'],'quote':quote,'reason':reason})
    if (excluded or summaries or blocked_assertions) and not validated_flags:
        raise ProposalError('Excluding a candidate requires a source-grounded assessment flag')
    updated=deepcopy(frontier)
    excluded_set=set(excluded); blocked=set(summaries); excluded_labels=set(blocked_assertions)
    updated['inferences']=[item for index,item in enumerate(proposals) if index not in excluded_set]
    updated['hypotheses']=[h for h in hypotheses if h['summary'] not in blocked]
    return {
        'frontier': updated,
        'new_claims':[c for c in new_claims if c['semantic_label'] not in excluded_labels],
        'assessment': {
            'policy': 'impact_aware',
            'model_review_performed': True,
            'excluded_inference_indices':sorted(excluded_set),
            'excluded_assertion_labels':sorted(excluded_labels),
            'excluded_hypothesis_summaries':sorted(blocked),
            'flags':validated_flags,
            'limitation':'Model critique is not independent engineering verification',
            'reason':str(result.get('reason',''))[:600],
        },
    }
