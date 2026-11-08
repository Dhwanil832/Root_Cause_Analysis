"""First-admissible baseline: the model order determines the chosen action.

No causal-gap relevance calculation or cross-need route-access planning.
Scores are shown for diagnostics but intentionally do not reorder actions.
"""
from reasoning.lead.components.priority_scoring import score_action


def rank(runtime,actions,public):
    result=[]
    for item in actions[:20]:
        if not isinstance(item,dict):continue
        score=score_action(runtime,item,public)
        if score is not None:
            result.append({'action':item,'score':score,
                           'breakdown':{'policy':'first_admissible_model_order'}})
    return result
