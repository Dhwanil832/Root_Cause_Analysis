"""Public-context membrane for every model call.

It enforces key-level test-fixture isolation recursively and clones the
permitted context, so model adapters and role-specific policies cannot mutate
the shared case state through a referenced nested Python object.

This cannot prevent accidental semantic spoilers inside allowed document TEXT;
that must be controlled by the host fixture's evidence-release protocol.
"""
from __future__ import annotations
from copy import deepcopy

HIDDEN_FIELDS={
    'gold_answer','gold_answers','designer_reference','private_reference',
    'hidden_document','hidden_documents','author_only','fixture_responses',
    'answer_key','evaluation_rubric','reference_causal_chart',
}


def _ensure_public(obj,path='context',depth=0):
    if depth>45:raise ValueError('Agent context nesting exceeds safe depth')
    if isinstance(obj,dict):
        for key,value in obj.items():
            if isinstance(key,str) and key.lower() in HIDDEN_FIELDS:
                raise ValueError('Forbidden private field in model context: '+path+'.'+key)
            _ensure_public(value,path+'.'+str(key),depth+1)
    elif isinstance(obj,(list,tuple)):
        for i,value in enumerate(obj):
            _ensure_public(value,path+f'[{i}]',depth+1)
    elif isinstance(obj,(str,int,float,bool,type(None))):
        return
    else:
        raise ValueError('Unexpected non-serializable value in model context: '+type(obj).__name__)


def build_agent_context(payload):
    if not isinstance(payload,dict):
        raise ValueError('Agent context must be an object')
    _ensure_public(payload)
    return deepcopy(payload)
