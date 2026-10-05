"""Aggregate fully reviewed semantic annotations. No keyword-based automatic grading."""
import argparse, collections, hashlib
from pathlib import Path
from common import PACKAGE, read, save
def make_report(run):
    pass  # Standalone comparison report is built separately.

def score(folder):
    folder=Path(folder).resolve();rows=read(folder/'annotations.json');criteria=read(PACKAGE/'private/evaluator/criteria.json')
    ids=[r['criterion_id'] for r in rows]
    if len(ids)!=len(set(ids)) or set(ids)!={c['id'] for c in criteria}:raise ValueError('Exactly 96 unique frozen criteria are required')
    windows=read(folder/'stage-windows.json')
    if set(windows)!={c['stage'] for c in criteria} or not all(windows.values()):raise ValueError('Document the 12 stage windows and exposure/absence before grading')
    for row in rows:
        if row['outcome'] not in ['Present','Missing','Not reached','Harness blocked']:raise ValueError('Unreviewed criterion: '+row['criterion_id'])
        if not all(row.get(k) for k in ['exposure','output_reference','excerpt_or_absence_reason','failure_origin','reviewer']):raise ValueError('Incomplete annotation: '+row['criterion_id'])
        if type(row['contradiction']) is not bool:raise ValueError('Explicit contradiction true/false required')
        if row['contradiction'] and not row.get('contradiction_reference'):raise ValueError('Contradiction requires its own citation')
        hashes={}
        for ref in row['output_reference']:
            f,_,pointer=ref.partition('#');p=(folder/f).resolve()
            if folder not in p.parents or not p.is_file():raise ValueError('Invalid evidence path: '+ref)
            if row['outcome']=='Present' and p.name!='answer.txt':raise ValueError('Presence requires newly emitted model text, not an input packet')
            if pointer:
                value=read(p)
                for part in pointer.lstrip('/').split('/'):
                    part=part.replace('~1','/').replace('~0','~');value=value[int(part)] if isinstance(value,list) else value[part]
            hashes[f]=hashlib.sha256(p.read_bytes()).hexdigest()
        row['verified_output_hashes']=hashes
    counts=collections.Counter(r['outcome'] for r in rows)
    result=dict(denominator=96,outcomes=dict(counts),presence_score=None if counts['Harness blocked'] else counts['Present'],consistent_score=None if counts['Harness blocked'] else sum(r['outcome']=='Present' and not r['contradiction'] for r in rows),stages=[])
    for stage in sorted(windows):
        rr=[r for r in rows if r['criterion_id'].startswith(stage+'.')];cc=collections.Counter(r['outcome'] for r in rr)
        result['stages'].append(dict(stage=stage,denominator=8,outcomes=dict(cc),presence_score=None if cc['Harness blocked'] else cc['Present'],consistent_score=None if cc['Harness blocked'] else sum(r['outcome']=='Present' and not r['contradiction'] for r in rr)))
    save(folder/'reviewed-annotations.json',rows);save(folder/'score-summary.json',result)
    run=next((p for p in folder.parents if (p/'plan.json').exists()),None)
    if run:make_report(run)
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('repetition_folder',type=Path);a=ap.parse_args();print(score(a.repetition_folder))
