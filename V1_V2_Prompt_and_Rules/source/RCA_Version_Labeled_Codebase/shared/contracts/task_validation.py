"""Task-specific model-response contracts with actionable errors and no coercion.

Transport JSON decoding is weaker than these operational contracts. They do
not certify semantic entailment; that needs the Assessor and external review.
"""
from __future__ import annotations
from shared.validation import ProposalError


class TaskContractError(ProposalError):
    """Schema/visibility issue that a model may correct on a bounded retry."""


def _array(obj, key, limit=30, optional=False):
    if optional and key not in obj:
        return []
    val = obj.get(key)
    if not isinstance(val, list) or len(val) > limit:
        raise TaskContractError(f'{key} must be an array of at most {limit} items')
    if any(not isinstance(x, dict) for x in val):
        raise TaskContractError(f'{key} entries must be objects')
    return val


def _fields(obj, fields, what):
    for key in fields:
        if not isinstance(obj.get(key), str) or not obj[key].strip():
            raise TaskContractError(f'{what}.{key} must be nonempty text')


def _quote(quote, payload):
    source = payload.get('document', {})
    text = source.get('text', '') if isinstance(source, dict) else ''
    if not isinstance(quote, str) or len(quote.strip()) < 8 or quote not in text:
        raise TaskContractError('A proposed quotation was not an exact substring of the current document')


def validate(task, answer, payload):
    if not isinstance(answer, dict):
        raise TaskContractError('The agent must return one JSON object')
    if task == 'extract':
        for x in _array(answer, 'assertions', 24):
            _fields(x, ('semantic_label','subject','predicate','scope','configuration','quote','basis'),'assertions[]')
            _quote(x['quote'], payload)
        for x in _array(answer, 'corrections', 18):
            _fields(x, ('target_source','quote','reason'),'corrections[]')
            _quote(x['quote'], payload)
            if not isinstance(x.get('target_claim_ids'), list):
                raise TaskContractError('corrections[].target_claim_ids must be a list')
    elif task == 'frontier':
        for x in _array(answer, 'hypotheses', 25):
            _fields(x, ('summary','why'),'hypotheses[]')
            for key in ('missing_conditions','tests'):
                if not isinstance(x.get(key), list):
                    raise TaskContractError(f'hypotheses[].{key} must be an array')
        for x in _array(answer, 'new_gaps', 25):
            _fields(x, ('semantic_label','kind','question','why','expected_change','quote'),'new_gaps[]')
            _quote(x['quote'], payload)
            if x['kind'] not in {'causal','operational','access'}:
                raise TaskContractError('Unsupported gap kind')
            if not isinstance(x.get('routes_to_consider',[]),list):
                raise TaskContractError('new_gaps[].routes_to_consider must be an array')
        for x in _array(answer, 'hypothesis_updates', 16, optional=True):
            _fields(x, ('hypothesis_id','status','reason','quote'),'hypothesis_updates[]')
            _quote(x['quote'],payload)
        for x in _array(answer, 'resolved_gaps', 20):
            _fields(x,('gap_id',),'resolved_gaps[]')
            if not isinstance(x.get('supporting_assertion_labels'),list):
                raise TaskContractError('resolved_gaps[].supporting_assertion_labels must be a list')
        for x in _array(answer, 'inferences', 20):
            _fields(x, ('subject','predicate','scope','warrant','quote'),'inferences[]')
            _quote(x['quote'], payload)
            if not isinstance(x.get('premise_claim_ids'),list):
                raise TaskContractError('inferences[].premise_claim_ids must be a list')
    elif task == 'propose_actions':
        for x in _array(answer, 'actions', 20):
            mode=x.get('mode')
            if mode not in {'discover','request','wait'}:
                raise TaskContractError('Unknown action mode')
            if mode!='wait':
                _fields(x, ('gap_id','route','question','information_needed','possible_effect'),'actions[]')
    elif task == 'plan_route':
        if answer.get('decision') not in {'execute','redirect','hold'}:
            raise TaskContractError('Route decision must be execute, redirect or hold')
        _fields(answer,('reason',),'route decision')
        if answer['decision']!='hold':
            _fields(answer,('route','question','information_needed'),'route decision')
    elif task == 'review_assessment':
        for key in ('exclude_inference_indices','exclude_hypothesis_summaries','exclude_assertion_labels','flags'):
            if not isinstance(answer.get(key),list):
                raise TaskContractError(f'assessor {key} must be an array')
        for f in answer['flags']:
            if not isinstance(f,dict) or not isinstance(f.get('reason'),str):
                raise TaskContractError('Assessor flags require objects with reasons')
            _quote(f.get('quote'),payload)
    else:
        raise TaskContractError(f'Unknown model task {task}')
    return answer
