"""Human review instrument: each model commitment must be judged in context."""
from __future__ import annotations
import csv,json
from pathlib import Path

COLUMNS=['case','item_type','id','status','statement','source_id','source_quote',
         'asset_time_scope_correct','quote_entails_claim','causal_warrant_valid',
         'support_independent','unsupported_commitment','reviewer_rationale']


def write_sheet(run_dir, destination):
    summary=json.loads((Path(run_dir)/'summary.json').read_text())
    rows=[];case=summary.get('case')
    for claim in summary.get('claims',[]):
        rows.append([case,'claim',claim.get('claim_id',''),claim.get('status',''),
                     ' | '.join(str(claim.get(k,'')) for k in ('subject','predicate','scope','configuration')),
                     claim.get('first_source',''),claim.get('quote',''), *(['']*6)])
    for hyp in summary.get('hypotheses',[]):
        rows.append([case,'candidate_hypothesis',hyp.get('id',''),hyp.get('status',''),
                     hyp.get('summary',''),hyp.get('origin_source',''),'', *(['']*6)])
    for link in summary.get('causal_view',{}).get('links',[]):
        rows.append([case,'causal_link',link.get('id',''),link.get('status',''),
                     str(link.get('causes',[]))+' -> '+str(link.get('effect','')),
                     '',str(link.get('rationale','')), *(['']*6)])
    dest=Path(destination);dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(COLUMNS);w.writerows(rows)
    return len(rows)
