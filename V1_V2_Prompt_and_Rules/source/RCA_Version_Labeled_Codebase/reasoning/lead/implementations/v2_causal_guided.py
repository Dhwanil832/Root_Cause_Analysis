"""Single-frontier planner: prioritize direct tests of causal uncertainties.

Discovery is possible but costs a step. Unlike the joint policy this method
does NOT model the value of unlocking a shared evidence route.
"""
from reasoning.lead.components.priority_scoring import score_action
from reasoning.lead.components.planning_features import score_record


def rank(runtime,actions,public):
    ranked=[]
    for item in actions[:20]:
        if not isinstance(item,dict):continue
        base=score_action(runtime,item,public)
        if base is None:continue
        ranked.append(score_record(runtime,item,public,base,'causal_guided'))
    return sorted(ranked,key=lambda item:(-item['score'],
        item['action']['route'],item['action']['gap_id']))
