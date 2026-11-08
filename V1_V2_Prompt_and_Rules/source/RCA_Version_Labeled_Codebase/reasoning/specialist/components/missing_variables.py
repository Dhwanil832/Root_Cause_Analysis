"""Deduplicate model-proposed gaps, preserving explicit source grounding."""
from __future__ import annotations

def normalize_frontier(raw,public):
    if not isinstance(raw,dict):raise ValueError('Specialist must return a JSON object')
    result=dict(raw)
    already={str(g.get('question','')).strip().lower() for g in public.get('gaps',[])}
    seen=set()
    out=[]
    for g in (raw.get('new_gaps') or [])[:25]:
        if not isinstance(g,dict):continue
        q=str(g.get('question','')).strip().lower()
        if not q or q in seen or q in already:continue
        seen.add(q);out.append(g)
    result['new_gaps']=out
    hypotheses=[]; seen_h=set()
    for h in (raw.get('hypotheses') or [])[:25]:
        if not isinstance(h,dict):continue
        summary=str(h.get('summary','')).strip().lower()
        if not summary or summary in seen_h:continue
        seen_h.add(summary);hypotheses.append(h)
    result['hypotheses']=hypotheses
    return result
