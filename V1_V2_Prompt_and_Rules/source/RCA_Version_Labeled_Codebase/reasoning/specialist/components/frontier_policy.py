"""Causal-frontier policy: distinct open questions, explicit conditional support.

This is an executable proposal-transform algorithm, NOT causal discovery from
physical dynamics and NOT a reimplementation of IRIS. It checks logical shape,
tracks hypothesis-to-question relevance, and identifies candidate omissions.
"""
from __future__ import annotations
import re
from copy import deepcopy
from shared.validation import ProposalError
from reasoning.specialist.components.missing_variables import normalize_frontier

STOPWORDS={'the','and','that','this','with','from','for','was','were','would','could','should',
           'into','what','when','why','how','which','where','whether','their','there','does',
           'occur','occurred','need','evidence','about','before','after','report','reported',
           'incident','information','mechanism','cause','caused','source','might','have','been'}


def terms(text):
    if not isinstance(text,str):return set()
    return {x for x in re.findall(r'[a-z0-9]+',text.lower()) if len(x)>2 and x not in STOPWORDS}


def overlap(a,b):
    a=terms(a);b=terms(b)
    return (len(a&b)/max(1,min(len(a),len(b)))) if a and b else 0.0


def related_hypotheses(gap,hypotheses):
    content=' '.join(str(gap.get(k,'')) for k in ('question','expected_change','semantic_label'))
    related=[]
    for h in hypotheses:
        material=' '.join([str(h.get('summary',''))]+[
            x for k in ('missing_conditions','tests') for x in h.get(k,[]) if isinstance(x,str)])
        if overlap(content,material)>=.24:
            related.append(str(h.get('summary','')))
    return related[:12]


def normalize_with_frontier(raw,public):
    result=normalize_frontier(raw,public)
    result=deepcopy(result)
    # Do not allow causal self-support or synonymously duplicated premises to
    # masquerade as two independent causal conditions.
    retained=[];deferred=[]
    for index,item in enumerate(result.get('inferences',[])):
        if not isinstance(item,dict):
            deferred.append({'index':index,'reason':'malformed_inference'})
            continue
        effect=item.get('effect_claim_id')
        causes=item.get('cause_claim_ids',[])
        premises=item.get('premise_claim_ids',[])
        if not isinstance(causes,list) or not isinstance(premises,list):
            deferred.append({'index':index,'reason':'malformed_premises'})
            continue
        if effect and effect in causes:
            deferred.append({'index':index,'reason':'cause_equals_effect'})
            continue
        if len(premises)!=len(set(premises)):
            deferred.append({'index':index,'reason':'repeated_premise'})
            continue
        retained.append(item)
    result['inferences']=retained
    result['deferred_inference_candidates']=deferred
    # Tie future action selection to the actual frontier: which hypotheses
    # depend on a given information need, rather than mere existence of 2 Hs.
    hypotheses=list(public.get('hypotheses',[]))+list(result.get('hypotheses',[]))
    for gap in result.get('new_gaps',[]):
        gap['related_hypothesis_summaries']=related_hypotheses(gap,hypotheses)
    # The question-condition coverage matrix is a diagnostic over candidate
    # causal explanations, never an assertion that those conditions occurred.
    from reasoning.specialist.components.hypothesis_matrix import compile_matrix
    result['_frontier_method_audit'] = compile_matrix(
        hypotheses, result.get('new_gaps', []), public.get('gaps', []))
    return result
