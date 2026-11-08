"""Visible bipartite graph of unresolved needs and plausible custodians.

The graph is derived only from published gap hints and discovered route records.
A discovered route is not proof that a document exists; a failed query does not
refute any causal hypothesis. This is V2 route ranking, not V3 lookahead search.
"""
from __future__ import annotations
from reasoning.specialist.components.frontier_policy import overlap


def inspect_routes(gap, public, discoveries=()):
    gap_id = gap.get('id')
    discovered = {r.get('id') for r in public.get('routes',[])}
    hinted = {h['route']:h for h in gap.get('routes_to_consider',[])
              if isinstance(h,dict) and h.get('route')}
    # Public routes are allowed alternatives, but unhinted routes receive no
    # relevance credit unless their description matches the scope of the gap.
    for route in public.get('routes',[]):
        rid=route.get('id')
        if not rid:continue
        hinted.setdefault(rid,{'route':rid,'topic':route.get('description',''),
                               'directness':0,'burden':2})
    attempted = {(a.get('gap_id'),a.get('route')) for a in public.get('attempts',[])}
    prior_status = {(a.get('gap_id'),a.get('route')):a.get('status') for a in public.get('attempts',[])}
    all_gaps = [g for g in public.get('gaps',[]) if g.get('status')=='open']
    ranked=[]
    question = gap.get('question','')+' '+gap.get('expected_change','')
    for rid, hint in hinted.items():
        if (gap_id,rid) in attempted:continue
        covered=sum(any(h.get('route')==rid for h in other.get('routes_to_consider',[]) if isinstance(h,dict))
                    for other in all_gaps)
        specificity=max(overlap(question,hint.get('topic','')),0)
        direct=max(0,min(3,int(hint.get('directness',0))))
        burden=max(0,min(4,int(hint.get('burden',2))))
        ready=rid in discovered
        # These are ordinal priorities, not probabilities or a utility theorem.
        value=round(1.2*direct + 1.3*specificity + .45*min(4,covered)
                    + (1.2 if ready else 0) - .35*burden,3)
        ranked.append({'route':rid,'mode':'request' if ready else 'discover',
                       'score':value,'reason':{
                           'discovered':ready,'possible_open_gap_coverage':covered,
                           'scope_overlap':round(specificity,3),
                           'declared_directness':direct,'declared_burden':burden,
                           'prior_status':prior_status.get((gap_id,rid)),
                       }})
    return sorted(ranked,key=lambda x:(-x['score'],x['route']))[:12]
