const $ = x => document.getElementById(x);
let state, timer;
function el(tag,text,cls) {const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x;}
async function api(path,data) {const r=await fetch(path,data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{});const v=await r.json();if(!r.ok)throw Error(v.error||'Request failed');return v;}
function message(t,error=false){$('message').textContent=t;$('message').className=error?'error':'';}
function form(id) {
 const box=el('div'),txt=el('textarea'),file=el('input'),submit=el('button','Submit evidence');
 txt.placeholder='Your observation, answer, or availability limit';file.type='file';file.accept='.pdf,.txt,.md,.json';
 submit.disabled=!!state.run_active;box.append(txt,file,submit);
 submit.onclick=async()=>{
  submit.disabled=true;
  try {
   if(!txt.value.trim()&&!file.files.length)throw Error('Add an answer or choose a document.');
   const payload={request_id:id,answer:txt.value};
   if(file.files.length){
    const f=file.files[0];
    if(f.size>20000000)throw Error('Upload at most 20 MB. Nothing submitted.');
    const bytes=new Uint8Array(await f.arrayBuffer());let encoded='';
    for(let i=0;i<bytes.length;i+=8192)encoded+=String.fromCharCode(...bytes.subarray(i,i+8192));
    payload.filename=f.name;payload.file=btoa(encoded);
   }
   const result=await api('/submit',payload);
   message('Submission saved together: '+result.saved.map(x=>x.source_id+(x.changed?'':' (already received)')).join(', ')+'. Continue to assess it.');
   await refresh();
  }catch(e){message(e.message,true);}finally{submit.disabled=!!state.run_active;}
 };
 return box;
}
function showDiagnostics() {
 const host=$('diagnostics');host.replaceChildren();
 const d=state.diagnostics||{};
 const failure=d.error||d.server_error;
 if(failure)host.append(el('p',(failure.model?failure.model+': ':'')+failure.detail,'error'));
 if(d.feedback&&d.feedback.accepted===false){
  host.append(el('p','The last proposed update was rejected; nothing from that batch was committed.','error'));
  for(const e of d.feedback.errors||[]){
   host.append(el('p',[e.record_id?'Record '+e.record_id:'',e.detail||'',e.path||'',e.actual!==undefined?'Received '+JSON.stringify(e.actual):'',e.expected!==undefined?'Expected '+JSON.stringify(e.expected):'',e.repair||''].filter(Boolean).join(' · ')));
  }
 }
 if(failure||(d.feedback&&d.feedback.accepted===false)){
  const detail=el('details');detail.append(el('summary','Technical diagnostic and recovery details'),el('pre',JSON.stringify({error:failure,feedback:d.feedback},null,2)));host.append(detail);
 }
 if(state.pending_call&&!state.run_active){
  host.append(el('p','Attempt preserved: '+state.pending_call.path+'. Inspect the diagnostic before choosing recovery.'));
  const reason=el('input');reason.placeholder='Reason for a new attempt';reason.setAttribute('aria-label','Retry reason');
  const b=el('button','Schedule explicit retry');
  b.onclick=async()=>{try{await api('/retry',{reason:reason.value});message('Retry scheduled separately. Continue investigation to run it.');await refresh();}catch(e){message(e.message,true);}};
  host.append(reason,b,el('p','A saved completed result recovers through Continue without a new call. Scheduling a retry preserves the failed attempt and does not start a model call.','muted'));
 }else if(!d.error&&!d.server_error&&!(d.feedback&&d.feedback.accepted===false))host.append(el('p',state.run_active?'Investigation running. Evidence submission resumes when this invocation pauses.':'No current execution error.'));
}
function requestCard(item) {
 const r=item.record,card=el('div',undefined,'question');
 card.append(el('strong',r.claim),el('span',r.status,'badge'),el('p',`${r.asset} · ${r.window}`));
 card.append(el('p','Current acquisition fields: '+r.fields.join(', ')));
 if(item.coverage_decision)card.append(el('pre',item.coverage_decision));
 if(item.justification)card.append(el('pre',item.justification.reason));
 if(item.coverage&&item.coverage.length){
  const history=el('details');history.append(el('summary','Field coverage, sources and reopening explanations'));
  for(const c of item.coverage)history.append(el('pre',`v${c.version} · ${c.status}\nFields: ${c.fields.join(', ')}\nRemoved from open scope (see explanation): ${c.removed_fields.join(', ')}\nSources: ${c.sources.join(', ')}\n${c.reason}`));
  card.append(history);
 }
 if(RcaView.requestGroup(item)==='actionable')card.append(form(r.id));
 else if(r.status==='blocked')card.append(el('p','This route is blocked. Supply genuinely new evidence through unsolicited submission if a new route becomes available.','muted'));
 return card;
}
async function refresh() {
 clearTimeout(timer);state=await api('/state');
 $('heading').textContent=state.description;
 $('status').textContent=`${state.run_active?'running':state.phase} · ${state.calls.length} processed calls · ${state.attempt_count||state.calls.length} attempts · ${state.queue.length} queued`;
 $('run').disabled=!!state.run_active;
 $('decision').textContent=state.last_decision||'No accepted update yet.';
 $('proposal-label').textContent=RcaView.updateLabel(state.last_update);
 $('proposal').textContent=state.last_update?state.last_update.decision:'';
 showDiagnostics();
 for(const id of ['inbox','internal','request-history'])$(id).replaceChildren();
 for(const item of Object.values(state.ledger).filter(x=>x.record.kind==='request')){
  const group=RcaView.requestGroup(item);$(group==='actionable'?'inbox':group==='internal'?'internal':'request-history').append(requestCard(item));
 }
 if(!$('inbox').children.length)$('inbox').append(el('p','No questions currently need a user response.'));
 $('unsolicited').replaceChildren(form(null));graph();$('records').replaceChildren();
 for(const [id,item] of Object.entries(state.ledger)){
  if(item.record.kind==='request')continue;
  const d=el('details');d.append(el('summary',`${id} · ${RcaView.appearance(item).label}`),el('p',item.record.claim),el('small',`Sources: ${item.record.sources.join(', ')} · version ${item.version}`));
  if(item.justification)d.append(el('pre',item.justification.reason));
  if(item.human_review)d.append(el('pre',`Human review of v${item.human_review.version}: ${item.human_review.decision}\n${item.human_review.note}`));
  if(item.record.kind==='edge')d.append(el('p',`${item.record.mode}: ${item.record.from_ids.join(' + ')} → ${item.record.to_id}`));
  if(item.superseded_by)d.append(el('p','Superseded by '+item.superseded_by));
  if(!item.stale&&!item.superseded_by&&item.record.status!=='withdrawn'){
   const note=el('textarea');note.placeholder='Required: your review and evidence basis';d.append(note);
   for(const choice of ['approved','rejected']){
    const b=el('button',choice==='approved'?'Approve this version':'Reject this version');b.disabled=!!state.run_active;
    b.onclick=async()=>{try{await api('/review',{id,version:item.version,decision:choice,note:note.value});await refresh();}catch(e){message(e.message,true);}};d.append(b);
   }
  }
  $('records').append(d);
 }
 $('sources').replaceChildren();for(const s of Object.values(state.sources)){const d=el('details');d.append(el('summary',`${s.id} · ${s.title} · v${s.version}`),el('pre',s.content));$('sources').append(d);}
 $('events').textContent=JSON.stringify(state.events.slice(-20),null,2);
 if(state.run_active)timer=setTimeout(()=>refresh().catch(e=>message(e.message,true)),1500);
}
$('run').onclick=async()=>{try{$('run').disabled=true;const r=await api('/run',{max_calls:$('budget').value.trim()===''?null:Number($('budget').value)});message(r.message);await refresh();}catch(e){message(e.message,true);$('run').disabled=false;}};
$('refresh').onclick=()=>refresh().catch(e=>message(e.message,true));
function graph(){let host=$('graph');host.replaceChildren();let entries=Object.entries(state.ledger).filter(([id,x])=>x.record.kind==='node'&&!x.superseded_by&&x.record.status!=='withdrawn'),edges=Object.values(state.ledger).filter(x=>x.record.kind==='edge'&&!x.superseded_by&&x.record.status!=='withdrawn');if(!entries.length){host.append(el('p','The board will appear after intake.'));return}const ns='http://www.w3.org/2000/svg',sv=(t,a={})=>{let x=document.createElementNS(ns,t);for(let[k,v]of Object.entries(a))x.setAttribute(k,v);return x},levels=Object.fromEntries(entries.map(([k])=>[k,0]));for(let pass=0;pass<Math.min(entries.length,8);pass++){let changed=false;for(let e of edges){let r=e.record;if(r.status==='refuted')continue;let l=Math.min(8,1+Math.max(0,...r.from_ids.map(k=>levels[k]||0)));if((levels[r.to_id]||0)<l){levels[r.to_id]=l;changed=true}}if(!changed)break}let rows={},pos={};for(let [id]of entries){let l=levels[id];let row=rows[l]||0;rows[l]=row+1;pos[id]={x:30+l*290,y:35+row*135}}let width=320+Math.max(...Object.values(levels))*290,height=80+Math.max(...Object.values(rows))*135,svg=sv('svg',{width,height,viewBox:`0 0 ${width} ${height}`}),defs=sv('defs'),marker=sv('marker',{id:'arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:6,markerHeight:6,orient:'auto-start-reverse'});marker.append(sv('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:'#698092'}));defs.append(marker);svg.append(defs);let joins={};for(let item of edges){let r=item.record,t=pos[r.to_id];if(!t)continue;let j=joins[r.to_id]||0;joins[r.to_id]=j+1;let jx=t.x-48-(j%3)*13,jy=t.y+30+j*15,group=sv('g'),color=RcaView.appearance(item).stroke,title=sv('title');title.textContent=r.id+' — '+r.mode.toUpperCase()+': '+r.claim+' — '+RcaView.appearance(item).label;group.append(title);for(let f of r.from_ids){let a=pos[f];if(!a)continue;let path=sv('path',{d:`M ${a.x+220} ${a.y+42} C ${a.x+245} ${a.y+42},${jx-25} ${jy},${jx} ${jy}`,fill:'none',stroke:color,'stroke-width':1.5});if(RcaView.appearance(item).dashed)path.setAttribute('stroke-dasharray','5 4');group.append(path)}let diamond=sv('path',{d:`M ${jx} ${jy-6} L ${jx+6} ${jy} L ${jx} ${jy+6} L ${jx-6} ${jy} Z`,fill:'white',stroke:color});group.append(diamond);let out=sv('path',{d:`M ${jx+6} ${jy} L ${t.x} ${t.y+42}`,stroke:color,fill:'none','marker-end':'url(#arrow)'});if(RcaView.appearance(item).dashed)out.setAttribute('stroke-dasharray','5 4');group.append(out);let label=sv('text',{x:jx-10,y:jy-9,'font-size':9,fill:'#526276'});label.textContent=r.mode.toUpperCase()+(item.stale?' · STALE':'')+(item.review==='human_rejected'?' · REJECTED':'');group.append(label);svg.append(group)}for(let[id,item]of entries){let r=item.record,p=pos[id],g=sv('g'),rect=sv('rect',{x:p.x,y:p.y,width:220,height:120,rx:7,fill:RcaView.appearance(item).fill,stroke:RcaView.appearance(item).stroke});g.append(rect);let title=sv('title');title.textContent=r.claim;g.append(title);let words=r.claim.split(' '),lines=[''],line=0;for(let w of words){if((lines[line]+' '+w).length>29){line++;lines[line]=''}lines[line]+=(lines[line]?' ':'')+w}lines.slice(0,4).forEach((s,i)=>{let t=sv('text',{x:p.x+9,y:p.y+18+i*16,'font-size':11});t.textContent=s+(i===3&&lines.length>4?'…':'');g.append(t)});let t=sv('text',{x:p.x+9,y:p.y+104,'font-size':8,fill:'#526276'});t.textContent=RcaView.appearance(item).label+' · '+id;g.append(t);svg.append(g)}host.append(svg)}
refresh().catch(e=>message(e.message,true));
