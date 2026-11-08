#!/usr/bin/env python3
"""Build a self-contained HTML view of the final board in a closed-loop run output.

Reads a file written by run_v3_closed_loop.py and writes one HTML page: claims with
the distinct source sentences that support or contradict them, candidate causal
links, which documents were registered and which were ever assessed, requests, and
open needs. It shows recorded state only; it decides nothing about the incident.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RCA Board View</title>
<style>
:root{--ink:#142135;--muted:#607188;--line:#dae3ec;--blue:#235bc0;--green:#16784c;--red:#bc3e56;--amber:#a76a1e}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 system-ui,-apple-system,Segoe UI,Arial,sans-serif;color:var(--ink);background:#f4f7fa}
header{background:#10243d;color:#fff;padding:18px 28px;display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}
header h1{margin:0;font-size:20px}header p{margin:4px 0 0;color:#cad9ee;font-size:13px}
.flag{font-size:12px;background:#ffffff20;border:1px solid #ffffff50;padding:6px 12px;border-radius:30px;font-weight:700}
.wrap{max-width:1500px;margin:0 auto;padding:20px 26px 45px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}
.stat{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.stat b{display:block;font-size:22px}.stat span{font-size:12px;color:var(--muted)}
.grid{display:grid;grid-template-columns:1.5fr 1fr;gap:16px}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:16px;min-width:0}
h2{font-size:16px;margin:0 0 10px}.sub{font-size:12px;color:var(--muted);margin-top:3px;word-break:break-word}
.item{border-top:1px solid #edf0f4;padding:9px 0}.item:first-child{border-top:0}
.label{font-weight:650}.id{font:12px ui-monospace,Consolas,monospace;color:#51647c}
.badge{font-size:11px;border-radius:25px;padding:2px 8px;display:inline-block;font-weight:750;margin-left:6px}
.supports{color:var(--green);background:#e2f6eb}.contradicts{color:var(--red);background:#ffebee}
.neutral,.n{color:#51647c;background:#eef2f6}.warn{color:var(--amber);background:#fff1d8}.info{color:var(--blue);background:#e9f1ff}
details{padding-top:6px}summary{cursor:pointer;font-size:13px;font-weight:650}
.quote{border-left:3px solid #c9d6e6;padding:3px 10px;margin:5px 0;font-size:13px;background:#f8fafc}
.quote.supports{border-color:var(--green)}.quote.contradicts{border-color:var(--red)}
.empty{color:#91a0b4;font-style:italic}.note{background:#fff7e9;border-left:3px solid #c17934;padding:8px 12px;margin-bottom:16px;font-size:13px}
.legend{display:flex;flex-wrap:wrap;gap:8px 14px;font-size:12px;color:var(--muted);align-items:center}
.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:5px;vertical-align:-2px;border:2px solid}
.toolbar{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;justify-content:space-between;margin-bottom:10px}
.tb button{border:1px solid #b9ccdf;background:#fff;border-radius:6px;padding:4px 10px;font-size:12px;font-weight:650;cursor:pointer;margin-left:4px}
.tb button:hover{background:#e8f1ff}
.boardgrid{display:grid;grid-template-columns:minmax(0,1fr) 370px;gap:14px;align-items:start}
.viewport{border:1px solid var(--line);border-radius:10px;background:#eef2f6;overflow:auto;height:min(72vh,720px);position:relative;
 background-image:radial-gradient(#cdd6df 1px,transparent 1px);background-size:22px 22px}
.stage{position:relative}.stage svg{position:absolute;left:0;top:0;overflow:visible}
.nb{position:absolute;width:210px;height:78px;background:#fff;border:2px solid #b9c6d6;border-radius:8px;padding:5px 8px 5px 10px;cursor:pointer;
 display:flex;flex-direction:column;gap:2px;transition:opacity .15s}
.nb:hover{box-shadow:0 2px 8px #10243d30}
.nb.supports{background:#e2f6eb;border-color:#16784c}.nb.contradicts{background:#ffebee;border-color:#bc3e56}
.nb.mixed{background:#fff1d8;border-color:#a76a1e}.nb.neutral{background:#eef2f6;border-color:#8696ab}
.nb.never{border-style:dashed}.nb.root{border-width:3px;border-color:#10243d}
.nb.sel{box-shadow:0 0 0 4px #cfe0ff,0 0 0 6px var(--blue)}.nb.dim{opacity:.25}.nb.docmark{box-shadow:0 0 0 4px #ffe3b0,0 0 0 6px #c17934}
.nb .row{display:flex;justify-content:space-between;align-items:center;gap:6px;font:11px ui-monospace,Consolas,monospace;color:#51647c}
.nb .ev{font-weight:700;color:#142135}.nb .xp{border:1px solid #8aa0bb;border-radius:10px;padding:0 7px;background:#fff;font-weight:700;color:#235bc0}
.nb .xp:hover{background:#235bc0;color:#fff}
.nb .tx{font-size:12.5px;line-height:1.25;font-weight:550;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical}
path.e{fill:none;stroke:#b9c6d6;stroke-width:1.4;transition:opacity .15s}path.e.lk{stroke:#c17934;stroke-width:1.8;stroke-dasharray:6 4}
path.e.hl{stroke:#235bc0;stroke-width:2.6;stroke-dasharray:none}path.e.dimE{opacity:.12}
g.gate{cursor:pointer}g.gate circle{fill:#fff7e9;stroke:#c17934;stroke-width:1.8}g.gate.sel circle{fill:#ffe3b0;stroke-width:3}
g.gate text{font:700 10px ui-monospace,Consolas,monospace;fill:#142135}g.gate .sm{font:10px system-ui,Arial,sans-serif;fill:#607188;font-weight:400}
aside.panel{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px 16px;position:sticky;top:10px;max-height:min(72vh,720px);overflow:auto;min-width:0}
aside.panel h3{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:14px 0 6px}
aside.panel .stmt{font-size:15px;font-weight:600;margin:6px 0}
.pill{display:inline-block;border:1px solid #b9ccdf;border-radius:4px;padding:1px 7px;font-size:11.5px;margin:2px 4px 2px 0;background:#f8fafc;color:#235bc0;cursor:pointer;font-weight:600}
.pill:hover{background:#e8f1ff}.doclink{cursor:pointer;text-decoration:underline dotted}
.nl{display:flex;gap:8px;width:100%;text-align:left;background:none;border:0;padding:4px;border-radius:4px;font:inherit;font-size:13px;cursor:pointer}
.nl:hover{background:#eef4ff}.nl .id{min-width:70px}
.banner{background:#fff1d8;border-radius:6px;padding:6px 10px;font-size:12.5px;margin-bottom:8px}
.banner button{margin-left:8px;border:1px solid #a76a1e;background:none;border-radius:4px;cursor:pointer;color:#a76a1e}
.item.doc{cursor:pointer}.item.doc:hover{background:#f3f7fd}.item.doc.on{background:#fff1d8}
#boardCard.fs{position:fixed;inset:0;z-index:50;margin:0;border-radius:0;overflow:auto;background:#f4f7fa}
#boardCard:fullscreen{margin:0;border-radius:0;overflow:auto;background:#f4f7fa}
#boardCard.fs .viewport,#boardCard:fullscreen .viewport{height:calc(100vh - 130px)}
#boardCard.fs aside.panel,#boardCard:fullscreen aside.panel{max-height:calc(100vh - 130px);top:0}
@media(max-width:1000px){.grid,.boardgrid{grid-template-columns:1fr}aside.panel{position:static;max-height:none}}
@media(max-width:1000px){.grid{grid-template-columns:1fr}}
</style></head><body>
<header><div><h1>RCA board · final state of the run</h1><p id="case"></p></div><div class="flag" id="status"></div></header>
<div class="wrap">
<div class="note">Workflow output on synthetic fixtures. Candidate links are not conclusions, and no root cause has been decided here. A quote counts once however many times it was re-assessed.</div>
<div class="stats" id="stats"></div>
<section class="card" id="boardCard"><h2>RCA chart</h2>
<div class="toolbar"><div class="legend" id="legend"></div>
<div class="tb"><button id="fsBtn">⛶ Full screen</button><button id="expAll">Expand all</button><button id="colAll">Collapse all</button><button id="clrTrace">Clear trace</button></div></div>
<div class="boardgrid"><div><div class="viewport" id="viewport"><div class="stage" id="stage"><svg id="edges"></svg></div></div>
<div class="sub">Effect on the left, claims it was broken into on the right. Click a box to open it, see its evidence and trace its path back to the event; click the + chip to expand or collapse its sub-claims.</div></div>
<aside class="panel" id="panel"></aside></div></section>
<div class="grid"><div>
<section class="card"><h2>Claims and the evidence found for them</h2><div id="claims"></div></section>
<section class="card"><h2>Candidate causal links (not confirmed)</h2><div id="links"></div></section>
</div><div>
<section class="card"><h2>Documents: registered vs ever assessed</h2><div class="sub">Click one to see which claims it gave evidence for.</div><div id="materials"></div></section>
<section class="card"><h2>Requests for more evidence</h2><div id="requests"></div></section>
<section class="card"><h2>Open needs</h2><div id="needs"></div></section>
<section class="card"><h2>Jobs rejected during the run</h2><div id="failures"></div></section>
</div></div></div>
<script>
const D = __DATA__;
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const eff=a=>String(a.effect||'').split('.').pop().toLowerCase();
const st=v=>String(v||'').split('.').pop();
const badge=(t,c)=>`<span class="badge ${c||'n'}">${esc(String(t).replaceAll('_',' '))}</span>`;
const titleOf=Object.fromEntries(D.materials.map(m=>[m.material_id,m.title||m.material_id]));
$('case').textContent=`Case ${D.case_id}`;
$('status').textContent=D.status;
const assessedMats=new Set(D.assessments.map(a=>a.material_id));
const pairs=new Set(D.assessments.map(a=>a.claim_id+'|'+a.exact_text));
const counts=D.assessments.reduce((m,a)=>(m[eff(a)]=(m[eff(a)]||0)+1,m),{});
const stats=[[D.claims.length,'claims'],[D.links.length,'candidate causal links'],
 [D.materials.length,'documents registered'],[[...assessedMats].filter(x=>titleOf[x]).length,'documents ever assessed'],
 [D.assessments.length,'assessments (with repeats)'],[pairs.size,'distinct claim-sentence pairs'],
 [(counts.supports||0)+' / '+(counts.contradicts||0),'supports / contradicts'],[counts.neutral||0,'neutral'],
 [D.needs.filter(n=>st(n.state)==='open').length,'open needs']];
$('stats').innerHTML=stats.map(([v,l])=>`<div class="stat"><b>${esc(v)}</b><span>${esc(l)}</span></div>`).join('');
const byClaim={};for(const a of D.assessments)(byClaim[a.claim_id]??=[]).push(a);
function qinfo(id){const list=byClaim[id]||[];const m=new Map();
 for(const a of list){const e=eff(a);if(e==='neutral')continue;const k=e+'|'+a.exact_text;
  const q=m.get(k)||{e,t:a.exact_text,m:a.material_id,n:0,why:a.rationale};q.n++;m.set(k,q)}
 const quotes=[...m.values()];
 return {list,quotes,distinct:new Set(list.map(a=>a.exact_text)).size,
  s:quotes.filter(q=>q.e==='supports').length,x:quotes.filter(q=>q.e==='contradicts').length}}
// RCA chart: the reported event on the left, the claims it was broken into to the right; click to open and expand
(function chart(){
 const claims=Object.fromEntries(D.claims.map(c=>[c.claim_id,c]));
 const parents=id=>(claims[id].parent_claim_ids||[]).filter(p=>claims[p]);
 const kids={};for(const c of D.claims)for(const p of parents(c.claim_id))(kids[p]??=[]).push(c.claim_id);
 const roots=D.claims.filter(c=>!parents(c.claim_id).length).map(c=>c.claim_id);
 const linkById=Object.fromEntries(D.links.map(l=>[l.link_id,l]));
 const status=id=>{const q=qinfo(id);if(!q.list.length)return 'never';
  return q.s&&q.x?'mixed':q.s?'supports':q.x?'contradicts':'neutral'};
 const sty={supports:['#e2f6eb','#16784c','supporting quote found'],contradicts:['#ffebee','#bc3e56','contradicting quote found'],
  mixed:['#fff1d8','#a76a1e','both'],neutral:['#eef2f6','#8696ab','looked at, nothing relevant'],never:['#ffffff','#b9c6d6','never assessed']};
 $('legend').innerHTML=Object.entries(sty).map(([k,[f,s,t]])=>`<span><i style="background:${f};border-color:${s}${k==='never'?';border-style:dashed':''}"></i>${t}</span>`).join('')
  +'<span><i style="border-color:#c17934;background:#fff7e9;border-radius:50%"></i>candidate causal link</span><span>▲ supporting ▼ contradicting quotes</span>';
 const S={sel:roots[0],link:null,expanded:new Set(roots),trace:true,doc:null};
 const BW=210,BH=78,CW=BW+120,RG=14,PX=20,PY=20;
 const ancestors=id=>{const s=new Set(),up=x=>parents(x).forEach(p=>{if(!s.has(p)){s.add(p);up(p)}});up(id);return s};
 const docClaims=()=>S.doc?new Set(D.assessments.filter(a=>a.material_id===S.doc&&eff(a)!=='neutral').map(a=>a.claim_id)):null;
 function revealDoc(){for(const id of docClaims())ancestors(id).forEach(p=>S.expanded.add(p))}
 function render(){
  const depth={},row={};let next=0;
  const place=(id,d)=>{if(depth[id]!==undefined)return row[id];depth[id]=d;
   const ks=S.expanded.has(id)?(kids[id]||[]):[];
   if(!ks.length){row[id]=next++;return row[id]}
   row[id]=ks.map(k=>place(k,d+1)).reduce((a,b)=>a+b,0)/ks.length;return row[id]};
  roots.forEach(r=>place(r,0));
  const pos=id=>({x:PX+depth[id]*CW,y:PY+row[id]*(BH+RG)});
  const vis=Object.keys(depth);
  const path=new Set(S.trace&&!S.link?[S.sel,...ancestors(S.sel)]:[]);
  const near=new Set(S.trace&&!S.link?[...path,...(kids[S.sel]||[])]:[]);
  const dm=docClaims();
  // links: gate between the effect and its visible cause claims
  const gated=new Set();let gates='',edges='';
  const curve=(x1,y1,x2,y2,cls)=>{const m=(x1+x2)/2;return `<path class="e ${cls}" d="M${x1},${y1} C${m},${y1} ${m},${y2} ${x2},${y2}"/>`};
  for(const l of D.links){const t=l.target_claim_id;
   if(depth[t]===undefined||!S.expanded.has(t))continue;
   const srcs=(l.source_claim_ids||[]).filter(s=>depth[s]!==undefined);if(!srcs.length)continue;
   const tp=pos(t),gx=tp.x+BW+(CW-BW)/2,gy=srcs.reduce((a,s)=>a+pos(s).y+BH/2,0)/srcs.length;
   edges+=curve(tp.x+BW,tp.y+BH/2,gx-11,gy,'lk');
   for(const s of srcs){gated.add(t+'>'+s);edges+=curve(gx+11,gy,pos(s).x,pos(s).y+BH/2,'lk')}
   gates+=`<g class="gate${S.link===l.link_id?' sel':''}" data-link="${esc(l.link_id)}"><title>${esc(l.relation)} · ${esc(l.modality)} · ${esc(l.basis)}</title>
    <circle cx="${gx}" cy="${gy}" r="11"/><text x="${gx}" y="${gy+3.5}" text-anchor="middle">${esc(l.link_id)}</text>
    <text class="sm" x="${gx}" y="${gy-16}" text-anchor="middle">${esc(l.modality)}</text></g>`}
  for(const p of vis){if(!S.expanded.has(p))continue;
   for(const k of kids[p]||[]){if(depth[k]===undefined||gated.has(p+'>'+k))continue;
    const a=pos(p),b=pos(k),on=path.has(p)&&path.has(k)||(p===S.sel&&S.trace&&!S.link);
    edges+=curve(a.x+BW,a.y+BH/2,b.x,b.y+BH/2,on?'hl':(near.size&&!(near.has(p)&&near.has(k))?'dimE':''))}}
  let boxes='',W=0,H=0;
  for(const id of vis){const p=pos(id),c=claims[id],k=status(id),q=qinfo(id),n=(kids[id]||[]).length;
   W=Math.max(W,p.x+BW+PX);H=Math.max(H,p.y+BH+PY);
   const dim=(near.size&&!near.has(id))||(dm&&!dm.has(id)&&!(kids[id]||[]).some(x=>dm.has(x)));
   boxes+=`<div class="nb ${k}${roots.includes(id)?' root':''}${S.sel===id&&!S.link?' sel':''}${dim?' dim':''}${dm&&dm.has(id)?' docmark':''}" data-id="${esc(id)}" style="left:${p.x}px;top:${p.y}px" title="${esc(c.text)}">
    <div class="row"><span>${esc(id)}</span><span class="ev">${q.s?'▲'+q.s+' ':''}${q.x?'▼'+q.x:''}</span>${n?`<span class="xp" data-toggle="${esc(id)}">${S.expanded.has(id)?'−':'+'+n}</span>`:''}</div>
    <div class="tx">${esc(c.text)}</div></div>`}
  const stage=$('stage'),svg=$('edges');
  stage.style.width=W+'px';stage.style.height=H+'px';svg.setAttribute('width',W);svg.setAttribute('height',H);
  svg.innerHTML=edges+gates;stage.querySelectorAll('.nb').forEach(e=>e.remove());stage.insertAdjacentHTML('beforeend',boxes);
  panel();
 }
 function docName(id){return esc(titleOf[id]||id)}
 function nodeBtn(id){return `<button class="nl" data-go="${esc(id)}"><span class="id">${esc(id)}</span><span>${esc(claims[id].text)}</span></button>`}
 function panel(){
  let h='';
  if(S.doc)h+=`<div class="banner">Showing claims with evidence from <b>${docName(S.doc)}</b><button data-cleardoc>Clear</button></div>`;
  if(S.link){const l=linkById[S.link];
   h+=`<div class="id">${esc(l.link_id)} · candidate causal link</div><div class="stmt">${esc(l.relation)} · ${esc(l.modality)}</div>
    <span class="badge warn">${esc(st(l.status))}</span><span class="badge info">basis: ${esc(l.basis)}</span>
    <h3>Together these may cause</h3>${nodeBtn(l.target_claim_id)}
    <h3>Cause claims</h3>${(l.source_claim_ids||[]).filter(s=>claims[s]).map(nodeBtn).join('')}
    ${l.source_text?`<h3>Source text</h3><div class="quote">${esc(l.source_text)}</div>`:''}
    ${(l.source_refs||[]).length?`<h3>Documents</h3>${l.source_refs.map(r=>`<span class="pill" data-doc="${esc(r)}">${docName(r)}</span>`).join('')}`:''}
    <div class="sub">A candidate is a proposal to check, not a finding.</div>`;
  }else{
   const c=claims[S.sel],k=status(S.sel),q=qinfo(S.sel),[f,s,t]=sty[k];
   h+=`<div class="id">${esc(S.sel)} · ${esc(String(c.kind).replaceAll('_',' '))}${c.incident_status?' · '+esc(c.incident_status):''}</div><div class="stmt">${esc(c.text)}</div>
    <span class="badge" style="background:${f};color:${s}">${t}</span>
    <h3>Evidence</h3>`;
   if(q.quotes.length)h+=q.quotes.map(x=>`<div class="quote ${x.e}">${badge(x.e,x.e)} “${esc(x.t)}”<div class="sub"><span class="doclink" data-doc="${esc(x.m)}">${docName(x.m)}</span> · assessed ${x.n}×${x.why?' · '+esc(x.why):''}</div></div>`).join('');
   if(q.list.length)h+=`<div class="sub">${q.distinct} distinct sentence(s) looked at across ${q.list.length} assessment(s)${q.quotes.length?'':'; none supported or contradicted this claim'}.</div>`;
   else h+='<div class="sub">Never assessed against any document. No evidence either way.</div>';
   const pa=parents(S.sel),ks=kids[S.sel]||[];
   if(pa.length)h+=`<h3>Part of</h3>${pa.map(nodeBtn).join('')}`;
   if(ks.length)h+=`<h3>Sub-claims (${ks.length})</h3>${ks.map(nodeBtn).join('')}`;
   const ls=D.links.filter(l=>(l.source_claim_ids||[]).includes(S.sel)||l.target_claim_id===S.sel);
   if(ls.length)h+=`<h3>Candidate causal links</h3>`+ls.map(l=>`<button class="nl" data-link="${esc(l.link_id)}"><span class="id">${esc(l.link_id)}</span><span>${l.target_claim_id===S.sel?'effect of':'may cause'} · ${esc((l.source_claim_ids||[]).join(' + '))} → ${esc(l.target_claim_id)} (${esc(l.modality)})</span></button>`).join('');
   const prov=(c.provenance||[]).filter(x=>titleOf[x]);
   if(prov.length)h+=`<h3>Stated in</h3>${prov.map(x=>`<span class="pill" data-doc="${esc(x)}">${docName(x)}</span>`).join('')}`;
   const rq=D.requests.filter(r=>(r.target_ids||[]).includes(S.sel)),nd=D.needs.filter(n=>(n.target_ids||[]).includes(S.sel));
   if(rq.length)h+=`<h3>Requests for evidence</h3>`+rq.map(r=>`<div class="item"><div class="label" style="font-size:13px">${esc(r.wording)}</div><div class="sub">${esc(st(r.state))}</div></div>`).join('');
   if(nd.length)h+=`<h3>Open needs</h3>`+nd.filter(n=>st(n.state)==='open').map(n=>`<div class="item"><div style="font-size:13px">${esc(((n.slots||[])[0]||{}).description||n.need_id)}</div></div>`).join('');
  }
  $('panel').innerHTML=h;
 }
 const reveal=id=>{ancestors(id).forEach(p=>S.expanded.add(p))};
 function go(id){S.sel=id;S.link=null;S.trace=true;reveal(id);render();
  const e=$('stage').querySelector(`.nb[data-id="${CSS.escape(id)}"]`);if(e)e.scrollIntoView({behavior:'smooth',block:'nearest',inline:'nearest'})}
 $('stage').addEventListener('click',e=>{
  const t=e.target.closest('[data-toggle]');
  if(t){const id=t.dataset.toggle;S.expanded.has(id)?S.expanded.delete(id):S.expanded.add(id);render();e.stopPropagation();return}
  const g=e.target.closest('.gate');if(g){S.link=g.dataset.link;render();return}
  const b=e.target.closest('.nb');
  if(b){const id=b.dataset.id;const was=S.sel===id&&!S.link;S.sel=id;S.link=null;S.trace=true;
   if((kids[id]||[]).length&&!was)S.expanded.add(id);render();
   const el=$('stage').querySelector(`.nb[data-id="${CSS.escape(id)}"]`);if(el)el.scrollIntoView({behavior:'smooth',block:'nearest',inline:'nearest'})}});
 $('panel').addEventListener('click',e=>{
  const g=e.target.closest('[data-go]');if(g){go(g.dataset.go);return}
  const l=e.target.closest('[data-link]');if(l){S.link=l.dataset.link;render();return}
  const d=e.target.closest('[data-doc]');if(d){S.doc=S.doc===d.dataset.doc?null:d.dataset.doc;if(S.doc)revealDoc();render();return}
  if(e.target.closest('[data-cleardoc]')){S.doc=null;render()}});
 $('materials').addEventListener('click',e=>{const d=e.target.closest('[data-doc]');if(!d)return;
  S.doc=S.doc===d.dataset.doc?null:d.dataset.doc;if(S.doc)revealDoc();render();$('viewport').scrollIntoView({behavior:'smooth',block:'start'})});
 const card=$('boardCard'),fsBtn=$('fsBtn');
 const isFull=()=>document.fullscreenElement===card||card.classList.contains('fs');
 const syncFs=()=>{fsBtn.textContent=isFull()?'✕ Exit full screen':'⛶ Full screen'};
 function exitFull(){card.classList.remove('fs');if(document.fullscreenElement)document.exitFullscreen().catch(()=>{});syncFs()}
 fsBtn.onclick=()=>{if(isFull()){exitFull();return}
  // the browser's own full screen where allowed; otherwise fill the window
  const req=card.requestFullscreen?card.requestFullscreen():Promise.reject();
  Promise.resolve(req).catch(()=>{card.classList.add('fs')}).finally(syncFs)};
 document.addEventListener('fullscreenchange',syncFs);
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&card.classList.contains('fs'))exitFull()});
 $('expAll').onclick=()=>{D.claims.forEach(c=>{if((kids[c.claim_id]||[]).length)S.expanded.add(c.claim_id)});render()};
 $('colAll').onclick=()=>{S.expanded=new Set(roots);S.sel=roots[0];S.link=null;render()};
 $('clrTrace').onclick=()=>{S.trace=false;S.doc=null;render()};
 render();
})();
$('claims').innerHTML=D.claims.map(c=>{
 const list=byClaim[c.claim_id]||[];
 const quotes=new Map();
 for(const a of list){const e=eff(a);if(e==='neutral')continue;
  const k=e+'|'+a.exact_text;const q=quotes.get(k)||{e,t:a.exact_text,m:a.material_id,n:0,why:a.rationale};q.n++;quotes.set(k,q)}
 const distinct=new Set(list.map(a=>a.exact_text)).size;
 const s=[...quotes.values()].filter(q=>q.e==='supports').length,x=[...quotes.values()].filter(q=>q.e==='contradicts').length;
 const body=[...quotes.values()].map(q=>`<div class="quote ${q.e}">${badge(q.e,q.e)} “${esc(q.t)}”<div class="sub">${esc(titleOf[q.m]||q.m)} · assessed ${q.n}×${q.why?' · '+esc(q.why):''}</div></div>`).join('');
 return `<div class="item"><span class="label">${esc(c.text)}</span>${badge(c.kind,'info')}<div class="id">${esc(c.claim_id)}</div>
 <div class="sub">${list.length?`${distinct} distinct sentence(s) looked at · ${s} supporting · ${x} contradicting`:'<span class="warn badge">never assessed</span>'}</div>
 ${body?`<details open><summary>Evidence found</summary>${body}</details>`:''}</div>`}).join('')||'<p class="empty">No claims</p>';
$('links').innerHTML=D.links.map(l=>`<div class="item"><span class="label">${esc((l.source_claim_ids||[]).join(' + '))} → ${esc(l.target_claim_id)}</span>${badge(st(l.status),'warn')}
 <div class="sub">${esc(l.relation)} · ${esc(l.modality)} · basis: ${esc(l.basis)}</div>${l.source_text?`<details><summary>Source text</summary><div class="quote">${esc(l.source_text)}</div></details>`:''}</div>`).join('')||'<p class="empty">None</p>';
$('materials').innerHTML=D.materials.map(m=>`<div class="item doc" data-doc="${esc(m.material_id)}"><span class="label">${esc(m.title)}</span>${assessedMats.has(m.material_id)?badge('assessed','supports'):badge('never assessed','warn')}
 <div class="sub">${esc(m.source_kind)} · ${esc(m.lineage)}</div></div>`).join('');
$('requests').innerHTML=D.requests.map(r=>`<div class="item"><span class="label">${esc(r.wording)}</span>${badge(st(r.state),st(r.state)==='rejected'?'contradicts':'info')}
 <div class="sub">for ${esc((r.target_ids||[]).join(', '))}</div></div>`).join('')||'<p class="empty">None</p>';
$('needs').innerHTML=D.needs.filter(n=>st(n.state)==='open').map(n=>`<div class="item"><span class="label">${esc(((n.slots||[])[0]||{}).description||n.need_id)}</span>
 <div class="sub">${esc(n.origin_kind)} · for ${esc((n.target_ids||[]).join(', '))}</div></div>`).join('')||'<p class="empty">None open</p>';
$('failures').innerHTML=D.job_failures.map(f=>`<div class="item"><span class="label">${esc(f.role)} · ${esc(f.status)}</span><div class="sub">${esc(f.message||f.reason||'')}</div></div>`).join('')||'<p class="empty">None</p>';
</script></body></html>'''


def extract(report: dict[str, Any]) -> dict[str, Any]:
    board = report.get("board", {})
    meta = report.get("run_metadata", {})
    materials = [{k: m.get(k) for k in ("material_id", "title", "source_kind", "lineage")}
                 for m in board.get("materials", [])]
    assessments = [{k: a.get(k) for k in ("claim_id", "material_id", "exact_text", "effect", "rationale")}
                   for a in board.get("assessments", [])]
    return {
        "case_id": report.get("case_id", "unknown"),
        "status": meta.get("run_status", "unknown"),
        "claims": board.get("claims", []), "links": board.get("causal_links", []),
        "materials": materials, "assessments": assessments,
        "requests": board.get("requests", []), "needs": board.get("needs", []),
        "job_failures": meta.get("job_failures", report.get("job_failures", [])),
    }


def build(report: dict[str, Any]) -> str:
    data = json.dumps(extract(report), ensure_ascii=False, default=str).replace("</", "<\\/")
    return PAGE.replace("__DATA__", data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="run output JSON")
    parser.add_argument("--html", type=Path, help="destination (default: next to the input)")
    args = parser.parse_args()
    destination = args.html or args.output.with_suffix(".board.html")
    destination.write_text(build(json.loads(args.output.read_text(encoding="utf-8"))), encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
