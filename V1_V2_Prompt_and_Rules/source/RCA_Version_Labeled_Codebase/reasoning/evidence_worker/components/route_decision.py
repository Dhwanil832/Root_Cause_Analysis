"""Constrain evidence-worker proposals to visible custodians and scoped gaps.

The agent may redirect to a custodian only if it was a hypothesis-route hint
for the same gap or has already been discovered publicly. It never receives a
fixture file list, and cannot guess privileged filenames for direct retrieval.
"""
from __future__ import annotations
from shared.validation import ProposalError, bounded_str
from reasoning.lead.components.priority_scoring import score_action


def apply_route_plan(runtime, action, response, public):
    if not isinstance(response,dict):
        raise ProposalError('Evidence worker route decision must be a JSON object')
    decision=response.get('decision')
    if decision not in {'execute','redirect','hold'}:
        raise ProposalError('Evidence worker must choose execute, redirect or hold')
    reason=bounded_str(response.get('reason'),500)
    gid=action['gap_id']
    gap=runtime.gaps[gid]
    hinted={r.get('route') for r in gap.get('routes_to_consider',[]) if isinstance(r,dict)}
    discovered={r['id'] for r in public.get('routes',[])}
    eligible={action['route']} | hinted | discovered
    if decision=='hold':
        return None,{'decision':'hold','reason':reason,'eligible_routes':sorted(x for x in eligible if x)}
    route=response.get('route')
    if not isinstance(route,str) or route not in eligible:
        raise ProposalError('Evidence worker selected a route outside its public authorization')
    if decision=='execute' and route!=action['route']:
        raise ProposalError('Changing a route requires explicit redirect decision')
    mode='request' if route in discovered else 'discover'
    question=bounded_str(response.get('question',action.get('question','')),800)
    needed=bounded_str(response.get('information_needed',action.get('information_needed','')),800)
    if len(question)<12 or len(needed)<8:
        raise ProposalError('Evidence worker must state a meaningful scoped question and need')
    amended={**action,'mode':mode,'route':route,'question':question,'information_needed':needed}
    # Re-run lead admissibility: no requests to undiscovered custodians,
    # no duplicate route or already-covered gap, no route invented by the LLM.
    if score_action(runtime,amended,public) is None:
        raise ProposalError('Evidence worker proposed an inadmissible or already exhausted route')
    return amended,{
        'decision':decision,'reason':reason,'selected_mode':mode,'selected_route':route,
        'changed_route':route!=action['route'],
        'eligible_routes':sorted(x for x in eligible if x),
    }
