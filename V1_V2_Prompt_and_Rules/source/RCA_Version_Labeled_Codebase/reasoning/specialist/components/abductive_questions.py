"""Bounded missing-condition query generation from proposed hypotheses.

These are **information needs**, never incident findings. They are generated
only from a current source quote and already proposed conditional mechanisms.
Route hints must already have been proposed by the model for this case.
"""
from __future__ import annotations
from copy import deepcopy
from shared.validation import short_id
from reasoning.specialist.components.frontier_policy import overlap


def expand_one_gap(frontier,public):
    result=deepcopy(frontier)
    source=public.get('current_source',{})
    quotes=[c.get('quote','') for c in public.get('new_assertions',[])
            if isinstance(c,dict) and isinstance(c.get('quote'),str) and len(c['quote'])>=8]
    if not quotes or not source or not source.get('id'):
        result['generated_needs_audit']='No source-grounded assertion available'
        return result
    pool=[g for g in result.get('new_gaps',[])+public.get('gaps',[])
          if isinstance(g,dict) and g.get('routes_to_consider')]
    if not pool:
        result['generated_needs_audit']='No visible, nonprivileged route hints'
        return result
    existing=' '.join(str(g.get('question',''))+' '+str(g.get('expected_change',''))
                      for g in result.get('new_gaps',[])+public.get('gaps',[]))
    for hypothesis in result.get('hypotheses',[])[:8]:
        for condition in hypothesis.get('missing_conditions',[])[:6]:
            if not isinstance(condition,str) or not 8<=len(condition)<=160:
                continue
            # Do not clone an already asked question. Only one additional need
            # per newly delivered document, to bound request explosion.
            if overlap(condition,existing)>=.65:
                continue
            def match_strength(g):
                topic=' '.join(str(h.get('topic','')) for h in g.get('routes_to_consider',[])
                               if isinstance(h,dict))
                return max(overlap(condition,g.get('question','')+' '+g.get('expected_change','')),
                           overlap(condition,topic))
            closest=sorted(pool,key=match_strength,reverse=True)
            parent=closest[0]
            if match_strength(parent)<.18:
                continue  # Do not borrow a semantically unrelated custodian
            label='frontier_'+short_id('',hypothesis['summary']+'|'+condition)[:10]
            kind='operational' if any(x in condition.lower() for x in (
                'function','operat','designed','normal process')) else 'causal'
            result.setdefault('new_gaps',[]).append({
                'semantic_label':label,'kind':kind,
                'question':'What evidence could establish or refute this candidate condition: '+condition.rstrip('.?')+'?',
                'why':'Unverified condition for candidate: '+hypothesis['summary'][:250],
                'expected_change':'Evidence supporting or challenging '+condition,
                'quote':quotes[0],
                'routes_to_consider':deepcopy(parent.get('routes_to_consider',[])[:3]),
                'related_hypothesis_summaries':[hypothesis['summary']],
                'origin':'automatically_generated_inquiry_not_a_finding',
            })
            result['generated_needs_audit']='one missing hypothesis condition translated into a bounded information need'
            return result
    result['generated_needs_audit']='No uncovered missing condition identified'
    return result
