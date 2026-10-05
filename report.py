"""Read-only comparison report; scores come exclusively from reviewed annotations."""
import collections
import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WS = ROOT.parent


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def esc(value):
    return html.escape(str(value))


def link(path, label):
    return f'<a href="{esc(os.path.relpath(path, ROOT))}">{esc(label)}</a>'


def table(headers, rows):
    return '<table><thead><tr>' + ''.join(f'<th>{esc(x)}</th>' for x in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{x}</td>' for x in row) + '</tr>' for row in rows) + '</tbody></table>'


def main():
    entries = [
        ('GPT-5.5', ROOT/'scored-results/gpt', 'repaired/case', 'Historical scored fallback'),
        ('Qwen3.5', ROOT/'scored-results/qwen', 'case', 'Historical same-runtime attempt'),
        ('Granite 3.3 8B', ROOT/'scored-results/granite', 'case', 'New; CPU/GPU offload explicitly allowed'),
        ('Hermes 3 8B', ROOT/'scored-results/hermes', 'case', 'New; CPU/GPU offload explicitly allowed'),
        ('Mistral 7B', ROOT/'scored-results/mistral', 'case', 'New; full GPU'),
    ]
    if (ROOT/'runs/qwen/score-summary.json').exists():
        entries.append(('Qwen3.5 — fresh replication', ROOT/'runs/qwen', 'case',
                        'Two new calls; both answers byte-identical to historical fallback; original annotations verified and reapplied'))
    criteria = read(ROOT/'benchmark/R3-investigation-v1/private/evaluator/criteria.json')
    by_id = {c['id']: c for c in criteria}
    summary, data, details = [], [], []
    for name, folder, case, origin in entries:
        state = read(folder/case/'state.json', {})
        score = read(folder/'score-summary.json')
        status = read(folder/'status.json', {})
        nodes = [x for x in state.get('ledger', {}).values() if not x.get('superseded_by')]
        counts = collections.Counter(x['record']['kind'] for x in nodes)
        phase = state.get('phase') if state else status.get('phase', 'queued')
        if status.get('phase') == 'generating':
            phase = 'generating ' + status.get('role', '')
        label = lambda key: f"{score[key]}/96" if score and score.get(key) is not None else 'Pending'
        summary.append([esc(name), esc(origin), esc(phase), label('presence_score'), label('consistent_score'),
                        str(score['outcomes'].get('Not reached', 0)) if score else 'Pending',
                        f"{counts['node']} nodes / {counts['edge']} edges", str(len(state.get('calls', [])))])
        data.append(dict(model=name, origin=origin, phase=phase, score=score, active_records=dict(counts), completed_calls=len(state.get('calls', []))))
        content = f'<h2>{esc(name)}</h2><p>{esc(origin)}. {esc(phase)}.</p>'
        if state:
            content += '<p>' + link(folder/case/'state.json', 'Saved investigation state') + '</p>'
        if score:
            rows = []
            for stage in score['stages']:
                stage_name = next(c['stage_name'] for c in criteria if c['stage'] == stage['stage'])
                rows.append([esc(stage['stage']+' — '+stage_name), str(stage['presence_score'])+'/8',
                             str(stage['consistent_score'])+'/8', str(stage['outcomes'].get('Missing', 0)),
                             str(stage['outcomes'].get('Not reached', 0))])
            content += table(['Stage', 'Present', 'Consistent', 'Missing', 'Not reached'], rows)
            annotations = read(folder/'reviewed-annotations.json', [])
            if annotations:
                rows = []
                for a in annotations:
                    refs = []
                    for ref in a['output_reference']:
                        path, _, pointer = ref.partition('#')
                        refs.append(link(folder/path, path) + (' ' + esc(pointer) if pointer else ''))
                    rows.append([esc(a['criterion_id']), esc(by_id[a['criterion_id']]['expected']), esc(a['outcome']),
                                 esc(a['excerpt_or_absence_reason']), '<br>'.join(refs)])
                content += '<details><summary>All 96 expected-versus-observed checks</summary>' + table(['Check', 'Expected', 'Outcome', 'Observed / reason', 'Original output'], rows) + '</details>'
        else:
            content += '<p>No semantic score assigned yet. Pending is not zero.</p>'
        if nodes:
            content += '<details><summary>Retained board records</summary>' + table(['ID', 'Kind', 'Status', 'Claim', 'Connection'], [[esc(x['record']['id']), esc(x['record']['kind']), esc(x['record']['status']), esc(x['record']['claim']), esc(str(x['record'].get('from_ids', []))+' → '+str(x['record'].get('to_id') or ''))] for x in nodes]) + '</details>'
        if state.get('feedback', {}).get('accepted') is False:
            content += '<p><strong>Execution stop:</strong> ' + esc(state['feedback'].get('reason')) + '. The batch was rejected; raw answer content and committed records are evaluated separately.</p>'
        details.append(content)
    text = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>R3 fallback local-model comparison</title><style>
body{font:16px/1.5 system-ui,sans-serif;max-width:1400px;margin:40px auto;padding:0 24px;color:#17212c}h1{font-size:30px}h2{margin-top:38px}table{border-collapse:collapse;width:100%;font-size:14px;margin:18px 0}th,td{padding:10px;text-align:left;vertical-align:top;border:1px solid #dce1e7}th{background:#edf2f7}tr:nth-child(even){background:#fafbfd}summary{cursor:pointer;font-weight:600;padding:12px;background:#edf2f7}a{color:#145eaa}td{overflow-wrap:anywhere}details{margin:18px 0}@media print{details{display:block}body{margin:10px}table{font-size:10px}}
</style><h1>R3 — restored fallback comparison</h1>
<p>One connected attempt per new model. Same frozen fallback runtime, prompts, initial documents, custodian policy and 96-check rubric. GPT and Qwen are historical same-runtime baselines, not fresh repetitions.</p>
<p><strong>Present:</strong> expected meaning appears in original answers, including rejected proposals. <strong>Consistent:</strong> present without a recorded contradiction. <strong>Not reached:</strong> the required reasoning opportunity was never elicited; it is not an observed wrong answer. Board counts include unresolved/candidate edges and do not certify causal correctness.</p>
<p>Granite and Hermes required explicitly documented CPU offload at native 131k context; Mistral uses its native 32k context and full GPU. No added generation or call quota. Hardware differences are disclosed; latency is not a controlled comparison.</p>
<p>Single unblinded assistant review; this one-incident pilot does not establish general model reliability. GPT fallback remains partial and contains a known unsupported procedure-to-execution causal connection.</p>
<p><strong>Qwen replication:</strong> the separately labelled fresh run made two new model calls. Both requests, generated answers and validations match the historical fallback byte-for-byte. Its 17/96 score uses the original manual annotations after verifying exact output equivalence; this is not an independent second review. The older 49/96 clean-input and 7/96 connected scores came from different test settings.</p>
<p><strong>Why the local runs stop near S03:</strong> these are rubric groups applied to initial answers, not three successfully completed runtime stages. A failed lead batch commits no records, queues a correction and sets needs_attention; the runner then stops. The launcher does not automatically resume that correction. Later causal reasoning is unobserved.</p>'''
    text += table(['Model', 'Run / placement', 'State', 'Present', 'Consistent', 'Not reached', 'Saved board', 'Calls'], summary)
    text += '<p>' + link(ROOT/'provenance/PLAN.json', 'Frozen run plan and comparison limitations') + '</p>'
    text += ''.join(details) + '</html>'
    (ROOT/'REPORT.html').write_text(text)
    (ROOT/'comparison.json').write_text(json.dumps(data, indent=2)+'\n')
    print(json.dumps([dict(model=x['model'], phase=x['phase'], score=x['score']['presence_score'] if x['score'] else None) for x in data]))


if __name__ == '__main__':
    main()
