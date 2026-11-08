"""Research-inspired V2 Lead: single-step causal-question / route-coverage planning.

Unlike the V3 counterfactual proposal, this policy never simulates answers or
estimates a two-step Q function. Its computation is a cost-sensitive coverage
ranking on the visible frontier and publicly suggested evidence routes.
"""
from reasoning.lead.components.priority_scoring import score_action
from reasoning.lead.components.coverage_selection import rank_one_step


def rank(runtime,actions,public):
    return rank_one_step(runtime,actions,public,score_action)
