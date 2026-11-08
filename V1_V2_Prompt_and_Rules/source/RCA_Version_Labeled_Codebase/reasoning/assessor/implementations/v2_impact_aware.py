"""Enhanced assessor: second-model critique and bounded provenance-aware flags.

This explicitly invokes the configured Assessor model. Its quarantine decisions
must cite text from the *received* source and can only remove proposals, never
add support or perform unsourced revisions.
"""
from __future__ import annotations
from reasoning.assessor.components.proposal_review import apply_review
from reasoning.assessor.components.scope_guard import inspect_scope_risks


def review(runtime,source,state,extraction,frontier,new_claims):
    scope_audit = inspect_scope_risks(source,new_claims,frontier)
    view={
        'document':source,
        'existing_claims':state['existing_claims'],
        'new_assertions':new_claims,
        'existing_hypotheses':state['hypotheses'],
        'proposed_hypotheses':frontier.get('hypotheses',[]),
        'proposed_inferences':frontier.get('inferences',[]),
        'proposed_corrections':extraction.get('corrections',[]),
        'intake_structural_warnings':extraction.get('_intake_audit',{}).get('flags',[]),
        'deterministic_scope_review':scope_audit,
        'open_information_needs':state['gaps'],
        'instruction':'You may flag or quarantine proposals; do not invent evidence or commit changes.',
    }
    result=runtime.ask_role('assessor','review_assessment',view)
    reviewed = apply_review(source,frontier,result,new_claims)
    blocked = set(scope_audit['quarantine_assertion_labels'])
    if blocked:
        reviewed['new_claims'] = [c for c in reviewed['new_claims'] if c['semantic_label'] not in blocked]
    # If an assertion was quarantined, any proposed need resolution that
    # depended on that assertion must remain open. The raw source itself will
    # still be ingested. This avoids accidentally rejecting the whole source
    # on a dangling 'supporting_assertion_labels' link.
    allowed = {c['semantic_label'] for c in reviewed['new_claims']}
    remaining=[];suppressed=[]
    for resolution in reviewed['frontier'].get('resolved_gaps',[]):
        used=set(resolution.get('supporting_assertion_labels',[]))
        if not used or not used.issubset(allowed):
            suppressed.append(resolution.get('gap_id'))
        else:
            remaining.append(resolution)
    reviewed['frontier']['resolved_gaps']=remaining
    reviewed['assessment']['suppressed_gap_resolutions']=suppressed
    reviewed['assessment']['scope_guard'] = scope_audit
    reviewed['assessment']['scope_guard_quarantined'] = sorted(blocked)
    return reviewed


def postcommit(runtime,corrections):
    """Flag dependent hypothesis origins; never declare hypotheses disproven."""
    touched={item['target'] for item in corrections}
    affected=[]
    for h in runtime.hypotheses.values():
        if h.get('origin_source') in touched and h.get('status')=='candidate_not_proof':
            h['status']='needs_reassessment'
            h.setdefault('revisions',[]).append({
                'reason':'Origin source corrected; scoped candidate reassessment needed',
                'source':','.join(sorted(touched)),
                'heuristic_flag_only':True,
            })
            affected.append(h['id'])
    return affected
