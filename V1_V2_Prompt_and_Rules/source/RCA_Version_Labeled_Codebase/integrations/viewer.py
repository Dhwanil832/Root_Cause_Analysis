"""Generate an offline interactive step-through investigation from recorded state."""
from __future__ import annotations
import json
from pathlib import Path

HTML_TEMPLATE=r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Progressive RCA — Executed Investigation</title>
<style>
:root{color-scheme:light;--ink:#142135;--muted:#607188;--line:#dae3ec;--light:#f6f8fc;--blue:#235bc0;--green:#16784c;--red:#bc3e56;--amber:#a76a1e}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 system-ui,-apple-system,Segoe UI,Arial,sans-serif;color:var(--ink);background:#f4f7fa}
header{background:#10243d;color:white;padding:19px 28px;display:flex;justify-content:space-between;align-items:center;gap:16px}
header h1{margin:0;font-size:20px;font-weight:700}header p{margin:4px 0 0;color:#cad9ee;font-size:13px}
.flag{font-size:12px;background:#ffffff20;border:1px solid #ffffff50;padding:6px 12px;border-radius:30px;font-weight:700;white-space:nowrap}
.container{max-width:1540px;margin:0 auto;padding:22px 26px 45px}
nav{background:white;border:1px solid var(--line);border-radius:14px;padding:13px 16px;display:flex;align-items:center;gap:18px;margin-bottom:18px}
button{background:white;border:1px solid #b9ccdf;color:var(--ink);padding:9px 14px;border-radius:8px;font-weight:700;cursor:pointer}
button:hover{background:#e8f1ff}button:disabled{opacity:.45;cursor:not-allowed}input[type=range]{flex:1;accent-color:var(--blue)}
.step-count{white-space:nowrap;color:var(--muted);font-variant-numeric:tabular-nums;font-size:13px}
.top{display:grid;grid-template-columns:1.55fr 1fr;gap:16px;margin-bottom:16px}
.card{background:white;border:1px solid var(--line);border-radius:14px;padding:17px 19px;min-width:0}
h2{font-size:16px;margin:0 0 12px}h3{font-size:13px;margin:14px 0 8px;color:#344965}
p{margin:8px 0;color:#374962}
.event-name{font-size:23px;font-weight:800;letter-spacing:-.5px;margin-bottom:7px}
.mono{font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;color:#51647c;word-break:break-word}
.columns{display:grid;grid-template-columns:1.1fr 1fr 1fr;gap:16px}
.item{border-top:1px solid #edf0f4;padding:9px 0}.item:first-child{border-top:0}
.label{font-weight:680}.sub{font-size:12px;color:var(--muted);margin-top:3px}
.badge{font-size:11px;border-radius:25px;padding:3px 8px;display:inline-block;font-weight:750;margin-left:6px;letter-spacing:.1px}
.badge.supported,.badge.resolved,.badge.qualified_partial_support{color:var(--green);background:#e2f6eb}
.badge.unknown,.badge.open,.badge.needs_reassessment,.badge.reassessment_needed{color:var(--amber);background:#fff1d8}
.badge.candidate_not_proof,.badge.hypothesis_or_reassessment{color:var(--blue);background:#e9f1ff}
.badge.retired,.badge.excluded_for_this_mechanism,.badge.conflicted{color:var(--red);background:#ffebee}
.tally{font-size:12px;color:var(--muted);margin-bottom:8px}details{border-top:1px solid #e4ebf3;padding:8px 0}summary{font-weight:650;cursor:pointer}
.callout{border-left:3px solid var(--blue);padding:7px 12px;background:#f2f6fd;margin-top:10px}
.diff{border-left:3px solid #c17934;padding:6px 10px;background:#fff7e9;margin:5px 0;font-size:13px}
.footer{margin-top:18px;font-size:12px;color:#5e7086} .empty{color:#91a0b4;font-style:italic}
@media (max-width:1050px){.columns{grid-template-columns:1fr 1fr}.top{grid-template-columns:1fr}}
@media (max-width:690px){.columns{grid-template-columns:1fr}header{flex-direction:column;align-items:start}.container{padding:12px}nav{gap:8px;padding:9px}}
</style></head><body>
<header><div><h1>Progressive RCA · Executed investigation</h1><p>Incident investigation · evidence-aware reasoning · step-by-step trace</p></div><div class="flag" id="mode"></div></header>
<div class="container">
<nav><button id="prev">← Previous</button><input id="slider" type="range" min="0" value="0"><button id="next">Next →</button><strong id="counter" class="step-count"></strong></nav>
<div class="top">
<section class="card"><div class="event-name" id="event"></div><div class="mono" id="metadata"></div><div id="description"></div><div id="diffs"></div></section>
<section class="card"><h2>What the investigator can see</h2><div id="sources"></div><h3>Discovered evidence routes</h3><div id="routes"></div></section>
</div>
<div class="columns">
<section class="card"><h2>Causal evidence state</h2><div id="claim_count" class="tally"></div><div id="claims"></div><h3>Accepted causal links (qualified)</h3><div id="causal"></div></section>
<section class="card"><h2>Causal frontier</h2><div class="tally">Model-proposed alternatives. Never treated as incident facts by drawing them.</div><div id="hypotheses"></div></section>
<section class="card"><h2>Knowledge gaps / investigation agenda</h2><div class="tally">Operational, causal and access questions drive requests.</div><div id="gaps"></div></section>
</div><div class="footer">Execution label: <span id="foot_mode"></span>. Source quotations were checked for literal presence; this demonstration does not independently verify semantic entailment or physical causal truth. A fixture-provider run is not an autonomous LLM trial.</div>
</div>
<script>
const steps = __EMBED_STEPS__;
const meta = __EMBED_META__;
const $ = id=>document.getElementById(id);
let index=0;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const badge=(t)=>`<span class="badge ${esc(t)}">${esc(t).replaceAll('_',' ')}</span>`;
function stateChanges(a,b){if(!b)return [];
 const before=new Map(b.claims.map(c=>[c.claim_id,c.status]));
 const arr=[];for(const c of a.claims){const old=before.get(c.claim_id);if(old&&old!==c.status)arr.push(`${c.semantic_label}: ${old} → ${c.status}`)}
 return arr;
}
function render(){const s=steps[index], prev=index?steps[index-1]:null;
 $('counter').textContent=`${index+1} / ${steps.length}`;$('slider').value=index;
 $('prev').disabled=index===0;$('next').disabled=index===steps.length-1;
 $('event').textContent=(s.step?`Step ${s.step} · `:'')+s.event.replaceAll('_',' ');
 $('metadata').textContent=`Kernel revision ${s.kernel_revision} · ${s.source?('Source '+s.source):s.route?('Route '+s.route):''}`;
 const extras=['reason','selection_method','note','returned','via'];
 let desc=extras.filter(k=>s[k]).map(k=>`<p><strong>${esc(k.replaceAll('_',' '))}:</strong> ${esc(s[k])}</p>`).join('');
 if(s.selected_action){let a=s.selected_action;desc+=`<div class="callout"><strong>Chosen action:</strong> ${esc(a.mode)} ${esc(a.route||'')}<div class="sub">${esc(a.question||a.explanation||'')}</div><div class="sub">Information sought: ${esc(a.information_needed||'')}</div><div class="sub">Potential explanatory impact: ${esc(a.possible_effect||'')}</div></div>`;}
 if(s.alternatives?.length){desc+=`<details><summary>${s.alternatives.length} scored candidate actions</summary>`+s.alternatives.map(a=>`<div class="sub">${esc(a.mode)} ${esc(a.route)} / ${esc(a.gap_id)} · heuristic score ${esc(a.score)}</div>`).join('')+`</details>`;}
 if(s.correction_targets?.length)desc+=`<div class="callout"><strong>Correction committed:</strong> ${esc(s.correction_targets.join(', '))}</div>`;
 if(s.hypotheses_reassessed?.length)desc+=`<p><strong>Hypotheses reassessed:</strong> ${esc(s.hypotheses_reassessed.length)}</p>`;
 $('description').innerHTML=desc||'<p class="empty">No additional decision detail.</p>';
 const changes=stateChanges(s,prev);$('diffs').innerHTML=changes.length?`<h3>Changed evidence status</h3>`+changes.map(x=>`<div class="diff">${esc(x)}</div>`).join(''):'';
 $('sources').innerHTML=s.received_source_ids.length?s.received_source_ids.map(x=>`<span class="badge candidate_not_proof">${esc(x)}</span>`).join(' '):'<span class="empty">None received</span>';
 $('routes').innerHTML=s.routes.length?s.routes.map(x=>`<div class="item"><span class="label">${esc(x.id)}</span><div class="sub">${esc(x.description)}</div></div>`).join(''):'<p class="empty">No route discovered</p>';
 $('claim_count').textContent=`${s.claims.filter(x=>x.status==='supported').length} supported source/model assertions · ${s.claims.length} tracked`;
 $('claims').innerHTML=s.claims.map(c=>`<div class="item"><span class="label">${esc(c.semantic_label)}</span>${badge(c.status)}<div class="sub">${esc(c.predicate.replaceAll('_',' '))}</div><div class="sub">Scope: ${esc(c.scope)} · ${esc(c.configuration)} · ${esc(c.basis)}</div><details><summary>Provenance</summary><div class="sub">${esc(c.first_source)} · ${esc(c.origins.join(', ')||'no active origin')}</div><div class="sub">${esc(c.quote)}</div></details></div>`).join('')||'<p class="empty">No claims</p>';
 $('hypotheses').innerHTML=s.hypotheses.map(h=>`<div class="item"><span class="label">${esc(h.summary)}</span>${badge(h.status)}<div class="sub">Unresolved: ${esc(h.missing_conditions.join('; '))}</div><details><summary>Potential checks</summary><div class="sub">${esc(h.tests.join('; '))}</div></details></div>`).join('')||'<p class="empty">No candidates</p>';
 $('gaps').innerHTML=s.gaps.map(g=>`<div class="item"><span class="label">${esc(g.question)}</span>${badge(g.status)}<div class="sub">${esc(g.kind)} · ${esc(g.kernel_disposition||'not yet registered')}</div><div class="sub">${esc(g.expected_change)}</div>${g.coverage_invalidated?'<div class="diff">Previously used support was invalidated</div>':''}</div>`).join('')||'<p class="empty">No open questions</p>';
 $('causal').innerHTML=s.causal_view.links.length?s.causal_view.links.map(m=>`<div class="item"><span class="label">${esc(m.grade)}</span>${badge(m.status)}<div class="sub">Effect: ${esc(m.effect)}</div><div class="sub">Conditions: ${esc(m.causes.join(' + '))}</div></div>`).join(''):'<p class="empty">No assessed causal link yet</p>';
}
$('slider').max=steps.length-1;
$('slider').addEventListener('input',e=>{index=+e.target.value;render();});
$('prev').onclick=()=>{index=Math.max(0,index-1);render()};
$('next').onclick=()=>{index=Math.min(steps.length-1,index+1);render()};
$('mode').textContent=meta.provider_http_calls?`HTTP completions: ${meta.provider_http_calls}`:'AUTHOR-SUPPLIED FIXTURE MODEL';
$('foot_mode').textContent=meta.provider_http_calls?`${meta.provider_http_calls} external HTTP provider completions`:'Authored fixture-model responses; no fresh model inference';
render();
</script></body></html>'''

def build_viewer(trace_path,summary_path,destination):
    trace=json.loads(Path(trace_path).read_text())
    summary=json.loads(Path(summary_path).read_text())
    json_steps=json.dumps(trace,ensure_ascii=False).replace('</','<\\/')
    json_meta=json.dumps({'provider_http_calls':summary['provider_http_calls']}).replace('</','<\\/')
    text=HTML_TEMPLATE.replace('__EMBED_STEPS__',json_steps).replace('__EMBED_META__',json_meta)
    Path(destination).write_text(text)
    return str(destination)
