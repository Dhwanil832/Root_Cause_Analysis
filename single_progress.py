"""Build the single-repetition status table from saved artifacts; never infer scores."""
import html
import json
from pathlib import Path
from common import ROOT, read, save, now

OUT = ROOT / 'experiments/single-run-2026-10-05'


def build():
    plan = read(OUT / 'PLAN.json')
    statuses = {lane: read(OUT/(lane+'-status.json')) if (OUT/(lane+'-status.json')).exists() else {}
                for lane in ['local', 'gpt']}
    rows = []
    for entry in plan['models']:
        key = entry['key']
        folder = OUT / 'results' / key
        attempts = [read(p) for p in (folder/'clean/packets').glob('*/execution.json')]
        answers = sum(x['status'] in ['answer_saved', 'harness_validation_error'] for x in attempts)
        failed = sum(x['status'] in ['execution_failure', 'incomplete_preserved'] for x in attempts)
        clean_score_path = folder/'clean/score-summary.json'
        clean_score = read(clean_score_path) if clean_score_path.exists() else None
        if key in plan['existing_connected']:
            original = ROOT / plan['existing_connected'][key]
            conn_score = read(original/'score-summary.json')
            conn_count = 1
            conn_status = 'Existing same-runtime result, reused once'
        else:
            p = folder/'connected/execution-summary.json'
            connected = read(p) if p.exists() else None
            conn_count = 1 if connected and connected.get('calls', 0) else 0
            conn_status = connected['phase'] if connected else 'Pending'
            p = folder/'connected/score-summary.json'
            conn_score = read(p) if p.exists() else None
        lane = statuses['gpt' if key=='gpt' else 'local']
        active = key=='gpt' or lane.get('model')==entry['name']
        state = (lane.get('phase', 'queued') + (' '+lane['task'] if lane.get('task') else '')) if active else 'queued'
        if len(attempts)==17:
            state = 'Outputs saved; semantic review pending' if not clean_score else 'Reviewed'
        rows.append(dict(model=entry['name'], key=key, state=state,
            clean_answers=answers, clean_attempts=len(attempts), clean_execution_failures=failed,
            connected_attempts=conn_count, connected_status=conn_status,
            clean_score=clean_score, connected_score=conn_score))
    save(OUT/'TABLE.json', dict(at=now(), repetitions=1, rows=rows, statuses=statuses))
    esc=lambda x:html.escape(str(x))
    score=lambda x: str(x['presence_score'])+'/96' if x and x.get('presence_score') is not None else 'Pending'
    table=[]
    for row in rows:
        cells=[row['model'],row['state'],str(row['clean_answers'])+'/17',row['clean_execution_failures'],
               str(row['connected_attempts'])+'/1',score(row['clean_score']),score(row['connected_score'])]
        table.append('<tr>'+''.join('<td>'+esc(c)+'</td>' for c in cells)+'</tr>')
    headers=['Model','Current status','Clean answers saved','Clean execution failures','Connected attempts','Clean score','Connected score']
    doc='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="refresh" content="30"><title>Single-run R3 comparison</title><style>body{font:16px/1.5 system-ui;margin:30px;color:#17212c}table{border-collapse:collapse;width:100%}td,th{padding:12px;border:1px solid #ddd;text-align:left}th{background:#edf2f7}p{max-width:1150px}</style><h1>R3 benchmark — one repetition per model</h1><p>17 independent clean tasks and one connected investigation per model. Existing same-runtime connected results are reused once. Pending scores are not zero. Saved output is not automatically a correct answer; semantic review is separate.</p>'''
    doc+='<p>GPT clean transport stopped before an answer with “Your workspace is out of credits”; its existing connected result remains available. Local runs continue independently. The log also records earlier certificate failures before HTTPS fallback.</p>'
    doc+='<p>Updated: '+esc(now())+' (UTC).</p><table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join(table)+'</tbody></table>'
    doc+='<p>Connected scores measure expected meaning in raw answers; local historical runs with 74 unreached checks did not produce a board. Qualification and execution failures are not causal-reasoning scores.</p></html>'
    (OUT/'STATUS.html').write_text(doc)
    return rows


if __name__=='__main__':
    print(json.dumps([{k:r[k] for k in ['model','state','clean_answers','clean_execution_failures']} for r in build()]))
