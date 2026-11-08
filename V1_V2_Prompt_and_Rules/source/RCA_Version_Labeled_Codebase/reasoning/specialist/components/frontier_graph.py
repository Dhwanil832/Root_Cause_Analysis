"""Read the current *incomplete* causal structure and highlight unresolved premises.

This provides an evidence-grounded frontier to the Specialist. It does not
invent missing causal variables, claim that a hypothesis is true, or implement
IRIS. The LLM must propose actual explanatory alternatives for subsequent
human/model review and source-grounded validation.
"""
from __future__ import annotations

def inspect_frontier(session,limit=30):
    causal=session.causal_view()['links']
    claim_views=session.kernel.claim_views()
    unresolved=[]
    for link in causal:
        unknown=list(link.get('unresolved_conditions',[]))
        if unknown:
            unresolved.append({'causal_link_id':link.get('id'),
                 'status':link.get('status'),
                 'effect':link.get('effect'),
                 'missing_premises':unknown[:12]})
    contested=[{'key':key,'status':value['status']} for key,value in claim_views.items()
               if value['status']=='conflicting']
    # These are *observed/source-derived claims*, not proven causal origins.
    reported=[{'key':key,'status':value['status']} for key,value in claim_views.items()
              if value['status']=='supported']
    open_needs=[]
    for need_id in session.kernel.needs:
        view=session.kernel.need_view(need_id)
        if view['disposition'] not in {'covered','evidence_boundary'}:
            open_needs.append({'need_id':need_id,'disposition':view['disposition'],
              'uncovered':view['uncovered']})
    return {'unresolved_link_premises':unresolved[:limit],
            'contradictory_claims':contested[:limit],
            'supported_source_assertions':reported[:limit],
            'open_information_needs':open_needs[:limit],
            'warning':'This is incomplete evidence state, not a machine-discovered causal truth.'}
