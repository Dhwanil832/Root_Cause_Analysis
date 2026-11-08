"""Heuristic constraints: admissibility is separate from priority; NOT a calibrated VOI."""
from __future__ import annotations
import re

def score_action(self,action,public):
    """Transparent cost-conscious selector; ranking is heuristic, not calibrated VOI."""
    gid=action.get('gap_id','')
    if gid not in self.gaps or self.gaps[gid]['status']!='open':return None
    mode=action.get('mode')
    if mode not in {'discover','request'}:return None
    route=action.get('route','')
    if not isinstance(route,str) or not re.fullmatch(r'[a-zA-Z0-9_]{2,50}',route):return None
    discovered={r['id'] for r in public['routes']}
    if mode=='request' and route not in discovered:return None
    if mode=='discover' and route in discovered:return None
    if (gid,route) in {(a.get('gap_id'),a.get('route')) for a in self.attempts}:return None
    if mode=='request' and route in {a.get('route') for a in self.attempts if a.get('mode')=='request'}:
        # One fixture response per route. Retry against a different route, not same record.
        return None
    if mode=='discover' and route in {a.get('route') for a in self.discoveries}:
        return None
    if not isinstance(action.get('information_needed'),str) or len(action['information_needed'].strip())<8:return None
    if not isinstance(action.get('possible_effect'),str) or len(action['possible_effect'].strip())<8:return None
    try:
        direct=max(0,min(3,int(action.get('directness',1))))
        burden=max(0,min(4,int(action.get('burden',1))))
    except (ValueError,TypeError):return None
    g=self.gaps[gid]
    kind_value={'causal':2.0,'operational':1.5,'access':1.0}[g['kind']]
    route_value=1.0 if mode=='request' else .7
    tried=sum(x.get('gap_id')==gid for x in self.attempts)
    score=round(kind_value+1.2*direct+route_value-.7*burden-.8*tried,3)
    return score

