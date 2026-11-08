"""Active route planner: model proposes a scoped route; code validates access.

Unlike the baseline dispatcher this performs an Evidence Worker model call,
allows a safe redirect after new route information, tracks partial coverage and
makes failed discovery observable. It cannot use hidden custodian inventory.
"""
from __future__ import annotations
from reasoning.evidence_worker.components.route_decision import apply_route_plan
from reasoning.evidence_worker.components.route_map import inspect_routes


def execute(runtime,action):
    gid=action['gap_id']
    public=runtime.public_state()
    context={
        'proposed_action':dict(action),
        'open_gap':next((g for g in public['gaps'] if g['id']==gid),{}),
        'known_routes':public['routes'],
        'prior_attempts':[a for a in public['attempts'] if a.get('gap_id')==gid],
        'prior_discoveries':[
            {'gap_id':a.get('gap_id'),'route':a.get('route'),'found':a.get('found',[])}
            for a in runtime.discoveries if a.get('gap_id')==gid
        ],
        'ranked_public_route_candidates':inspect_routes(
            next((g for g in public['gaps'] if g['id']==gid),{}),public,runtime.discoveries),
        'instruction':'Choose an admissible route for the same information need, or hold. Rankings are fallible heuristics, not evidence.',
    }
    review=runtime.ask_role('evidence_worker','plan_route',context)
    selected,audit=apply_route_plan(runtime,action,review,public)
    audit={'gap_id':gid,'proposed_route':action['route'],**audit}
    runtime.routing_history.append(audit)
    runtime.record('evidence_route_decision',**audit)
    if selected is None:
        # An explicit hold is a bounded attempt, not a repeated non-executed loop.
        runtime.attempts.append({'mode':'hold','gap_id':gid,'route':action['route'],
                                 'status':'held_by_evidence_worker'})
        return False
    success=runtime._execute_baseline(selected)
    if selected['mode']=='discover':
        found=runtime.discoveries[-1].get('found',[])
        if not found:
            runtime.record('route_not_found',gap_id=gid,route=selected['route'],
                reason='No custodian matches public route query; reconsider alternative routes')
    elif selected['mode']=='request':
        last=runtime.attempts[-1]
        nid=runtime.gaps[gid].get('need_id')
        disposition=runtime.session.kernel.need_view(nid)['disposition'] if nid else 'untracked'
        if last.get('status')!='delivered' or disposition!='covered':
            runtime.record('evidence_coverage_incomplete',gap_id=gid,route=selected['route'],
                status=last.get('status'),disposition=disposition,
                reason='Returned evidence must be assessed against each requested field')
    return success
