"""Explainable planning features over an incomplete causal/evidence-access graph.

These are deterministic priorities, NOT probabilities, information gain, a
causal proof, or an optimal partially observable planner. All inputs are
available in the investigator's public case state.
"""
from __future__ import annotations
from reasoning.specialist.components.frontier_policy import overlap


def open_gaps(public):
    return [g for g in public.get('gaps',[]) if g.get('status')=='open']


def hypothesis_links(gap,public):
    linked=set(gap.get('related_hypothesis_summaries',[]))
    query=' '.join(str(gap.get(k,'')) for k in ('question','expected_change','semantic_label'))
    for h in public.get('hypotheses',[]):
        if not isinstance(h,dict):continue
        material=' '.join([str(h.get('summary',''))]+[
            x for k in ('missing_conditions','tests') for x in h.get(k,[]) if isinstance(x,str)])
        if overlap(query,material)>=.28:
            linked.add(str(h.get('summary','')))
    return linked


def frontier_relevance(gap,public):
    linked=hypothesis_links(gap,public)
    score=min(len(linked),3)*.70
    gf=public.get('graph_frontier',{})
    query=' '.join(str(gap.get(k,'')) for k in ('question','expected_change','semantic_label'))
    for link in gf.get('unresolved_link_premises',[]) if isinstance(gf,dict) else []:
        missing=' '.join(str(x) for x in link.get('missing_premises',[]))
        if overlap(query,missing)>=.20:
            score+=1.15
            break
    return round(score,3)


def route_reachability(route,public):
    """Count open information needs with a PUBLIC proposal for this custodian."""
    result=[]
    for gap in open_gaps(public):
        if any(h.get('route')==route for h in gap.get('routes_to_consider',[])
               if isinstance(h,dict)):
            result.append(gap)
    return result


def route_access_bonus(route,mode,public):
    coverage=route_reachability(route,public)
    direct=1.0 if mode=='request' else 0.45
    # Discovering a route may unlock several questions even though it returns
    # no physical evidence now. Scale is an ordinal heuristic, not expected IG.
    access=(.85*min(3,len(coverage))) if mode=='discover' else 0.0
    return round(direct+access,3),len(coverage)


def score_record(runtime,action,public,base,kind):
    gap=runtime.gaps[action['gap_id']]
    relevance=frontier_relevance(gap,public)
    burden=max(0,min(4,int(action.get('burden',1))))
    mode=action['mode']
    route=action['route']
    direct=max(0,min(3,int(action.get('directness',1))))
    uncertainty={'causal':1.6,'operational':.9,'access':.7}.get(gap.get('kind'),.7)
    if kind=='causal_guided':
        # Prefer immediate tests directly affecting unresolved causal questions.
        causal=uncertainty+relevance+(.55*direct)
        cost=.20*burden+(.8 if mode=='discover' else 0)
        access=0.0;reach=0
    elif kind=='joint_route_planner':
        # Couple causal-frontier importance with future source-route utility.
        access,reach=route_access_bonus(route,mode,public)
        causal=uncertainty+relevance+(.20*direct)
        cost=.27*burden+(.35 if mode=='discover' else 0)
    else:raise ValueError('Unknown planning strategy')
    total=round(base+causal+access-cost,3)
    return {'action':action,'score':total,'breakdown':{
        'admissible_base':base,'frontier_relevance':relevance,
        'causal_priority':round(causal,3),'route_access':access,
        'open_needs_accessible_via_route':reach,
        'time_cost_proxy':round(cost,3),
        'score_type':'ordinal_heuristic_not_expected_information_gain',
    }}
