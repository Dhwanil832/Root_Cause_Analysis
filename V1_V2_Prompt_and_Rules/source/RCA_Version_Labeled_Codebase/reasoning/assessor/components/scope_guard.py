"""Conservative source/applicability screen independent of the model critique.

These tests identify a few *mechanically recognizable* source-scope category
errors; they do not prove textual entailment, causal correctness or identity.
Only unambiguous scope mismatches are auto-quarantined. Ambiguous cases are
flags for the Assessor LLM and a later human reviewer, not factual rejections.
"""
from __future__ import annotations
import re

COND = re.compile(r'\b(may|might|could|would|assuming|hypothetical|possible|if|under normal)\b',re.I)
LATER = re.compile(r'\b(post[- ]?event|post[- ]?incident|later (?:bench |shop )?test|after the (?:accident|incident)|bench test)\b',re.I)
SCOPE_EVENT = re.compile(r'(?:^|[^a-z])(incident|event|during|\d\d[:_]\d\d)(?:$|[^a-z])',re.I)
PROVISIONAL = re.compile(r'\b(reportedly|believed|suspected|assumed|may|might|could|possibly|preliminary)\b',re.I)


def inspect_scope_risks(source, claims, frontier):
    quarantine = []
    risks = []
    for claim in claims:
        label = claim.get('semantic_label', '')
        q = str(claim.get('quote', ''))
        basis = str(claim.get('basis', ''))
        conf = str(claim.get('configuration', '')).lower()
        scope = str(claim.get('scope', '')).lower()
        pred = str(claim.get('predicate', '')).lower()
        current = (conf in {'incident','event'} or
                   (bool(SCOPE_EVENT.search(scope)) and not any(
                     x in scope for x in ('post_incident','post_event','later','after_incident'))))
        reason = None
        if current and basis == 'conditional_model' and COND.search(q):
            reason = 'A generic conditional equipment rule cannot establish incident-time occurrence'
        elif current and basis == 'documented_measurement' and LATER.search(q):
            reason = 'A later/post-incident measurement cannot be filed as incident-time measurement'
        if reason:
            quarantine.append(label)
            risks.append({'kind':'scope','severity':'quarantine','semantic_label':label,
                          'quote':q[:350],'reason':reason})
        else:
            if basis == 'assessed_source_assertion' and PROVISIONAL.search(q) and not any(
                    marker in pred for marker in ('reported','believed','possible','candidate','suspected')):
                risks.append({'kind':'modality','severity':'review','semantic_label':label,
                              'quote':q[:350],
                              'reason':'Source is qualified; check the proposed predicate preserves that qualification'})
            if current and LATER.search(q) and basis in {'assessed_source_assertion','action_status'}:
                risks.append({'kind':'time_scope','severity':'review','semantic_label':label,
                              'quote':q[:350],
                              'reason':'Later source observations or actions should not be promoted to incident-time events'})
    for i, inf in enumerate(frontier.get('inferences', []) if isinstance(frontier,dict) else []):
        if not isinstance(inf,dict):continue
        warrant = str(inf.get('warrant',''))
        if COND.search(warrant) and any(x in warrant.lower() for x in ('proves','establishes beyond doubt')):
            risks.append({'kind':'inference','severity':'review','inference_index':i,
                          'quote':str(inf.get('quote',''))[:350],
                          'reason':'A conditional premise appears paired with an unconditional certainty claim'})
    return {'quarantine_assertion_labels':sorted(set(quarantine)),
            'review_risks':risks[:24],
            'scope_guard_version':'v2_conservative_applicability_v1',
            'limitation':'Pattern-based risk screen; independent semantic entailment not established'}
