"""Five-agent V1 comparator: prompt-only route critique, no ranking algorithm.

Same autonomous role call and hard authorization checks as the V2 route worker,
but it sees only the Lead action and directly public route/attempt records; no
algorithmic ranked-route map is passed to the model.
"""
from reasoning.evidence_worker.components.route_decision import apply_route_plan


def execute(runtime, action):
    gid=action['gap_id']
    public=runtime.public_state()
    payload={'proposed_action':dict(action),
             'open_gap':next((g for g in public['gaps'] if g['id']==gid),{}),
             'known_routes':public['routes'],
             'prior_attempts':[a for a in public['attempts'] if a.get('gap_id')==gid],
             'prior_discoveries':[{'gap_id':a.get('gap_id'),'route':a.get('route'),'found':a.get('found',[])}
                                  for a in runtime.discoveries if a.get('gap_id')==gid]}
    decision=runtime.ask_role('evidence_worker','plan_route',payload)
    selected,audit=apply_route_plan(runtime,action,decision,public)
    runtime.routing_history.append({'gap_id':gid,**audit,'policy':'prompt_only'})
    runtime.record('evidence_route_decision',gap_id=gid,**audit)
    if selected is None:
        runtime.attempts.append({'mode':'hold','gap_id':gid,'route':action['route'],
                                 'status':'held_by_evidence_worker'})
        return False
    return runtime._execute_baseline(selected)
