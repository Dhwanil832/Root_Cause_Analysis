import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {localHttpOnce} from './local_http_once.mjs';
const dir=path.resolve(process.argv[2]||'');
const manifest=JSON.parse(await fs.readFile(path.join(dir,'manifest.json')));
const base=manifest.appUrl;
const prepared=process.argv.includes('--initialize-prepared');
if(!['http://127.0.0.1:3001','http://127.0.0.1:3002','http://127.0.0.1:3003'].includes(base)||manifest.batch!=='B0'||manifest.targetVersion!==1)throw Error('Only isolated B0/V1 is permitted');
const save=(name,data)=>fs.writeFile(path.join(dir,name),JSON.stringify(data,null,2),{flag:'wx'});
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
await save(prepared?'initialize-launch.json':'launch.json',{startedAt:new Date().toISOString(),pid:process.pid,initializeCallsPermitted:1,storyCallsPermitted:0,prepared});
async function request(route,options={}){
  if(options.long){
    const response=await localHttpOnce(base+route,{method:options.method||'GET',timeoutMs:3*60*60*1000});
    const body=JSON.parse(response.body);
    if(response.status<200||response.status>=300||body.error)throw Error(`${route}: ${body.error||response.status}`);
    return body;
  }
  const response=await fetch(base+route,{...options,signal:AbortSignal.timeout(options.long?3*60*60*1000:30000)});
  const raw=await response.text();let body;try{body=JSON.parse(raw);}catch{throw Error(`Non-JSON response ${response.status} at ${route}: ${raw.slice(0,160)}`);}
  if(!response.ok||body.error)throw Error(`${route}: ${body.error||response.status}`);
  return body;
}
let incidentId,trackId;
try{
  for(const [name,hash] of Object.entries(manifest.codeHashes)){
    if(sha(await fs.readFile(path.join(manifest.appDirectory,name)))!==hash)throw Error(`Frozen code changed: ${name}`);
  }
  for(const item of manifest.inputs){if(sha(await fs.readFile(path.join(dir,item.path)))!==item.sha256)throw Error(`Input changed: ${item.id}`);}
  const installed=await(await fetch('http://127.0.0.1:11434/api/tags')).json();
  const model=installed.models.find(m=>m.name==='qwen3.5:latest');
  if(model?.digest!==manifest.expectedModelDigest)throw Error('Qwen digest changed; no substitution');
  await save(prepared?'installed-model-at-dispatch.json':'installed-model.json',model);
  if(!prepared){
  const history=await request('/api/incidents'),library=await request('/api/references');
  if(history.incidents.length||library.documents.length)throw Error('Isolated database is not empty');
  await save('empty-state.json',{history,library});
  const refs=[];
  for(const item of manifest.inputs.filter(r=>r.scope==='default_reference')){
    const data=await fs.readFile(path.join(dir,item.path));const form=new FormData();
    form.set('file',new File([data],path.basename(item.path),{type:'text/markdown'}));
    form.set('title',path.basename(item.path));form.set('plant','IA-16036 evaluation');form.set('revision','B0');
    const response=await request('/api/references',{method:'POST',body:form});
    if(response.document.sha256!==item.sha256||response.document.extractionStatus!=='ready')throw Error(`Reference ingestion mismatch ${item.id}`);
    refs.push({recordId:item.id,document:response.document});
  }
  await save('reference-upload.json',refs);
  }
  const descriptionRecord=manifest.inputs.find(r=>r.scope==='incident_description');
  const description=(await fs.readFile(path.join(dir,descriptionRecord.path),'utf8')).trim();
  if(prepared){
    ({incidentId,trackId}=JSON.parse(await fs.readFile(path.join(dir,'identity.json'))));
    const failure=JSON.parse(await fs.readFile(path.join(dir,'failure.json')));
    const capture=await fs.readFile(path.join(dir,'capture-events.jsonl'),'utf8');
    if(failure.error!=='Error: Incident description mismatch'||capture.includes('"event":"request"'))throw Error('Prepared path only permitted after the zero-inference formatting preflight failure');
  }else{
  const form=new FormData();form.set('description',description);form.set('modelIds',JSON.stringify([manifest.model]));form.set('deferAnalysis','true');form.set('title','IA-16036 controlled B0 — Qwen — stop after V1');
  for(const item of manifest.inputs.filter(r=>r.scope==='starter_document'))form.append('files',new File([await fs.readFile(path.join(dir,item.path))],path.basename(item.path),{type:'text/markdown'}));
  const created=await request('/api/incidents',{method:'POST',body:form});incidentId=created.id;
  }
  const initial=await request(`/api/incidents/${incidentId}`);const track=initial.incident.tracks[0];trackId=track.id;
  if(!prepared)await save('identity.json',{incidentId,trackId,url:`${base}/incident/${incidentId}`});
  await save(prepared?'before-dispatch.json':'before-initialize.json',initial);
  if(initial.incident.tracks.length!==1||track.modelId!==manifest.model||track.versions.length)throw Error('Unexpected initial track/model/version');
  if(track.checkpoints.length)throw Error('A prior inference attempt exists; will not initialize again');
  const docs=track.documents;
  const expected=manifest.inputs.filter(r=>r.scope!=='incident_description');
  if(docs.length!==6||docs.filter(d=>d.scope==='reference').length!==3||docs.filter(d=>d.scope==='starter').length!==3)throw Error('Document isolation failed');
  for(const item of expected){
    const doc=docs.find(d=>d.sha256===item.sha256);
    if(!doc||doc.extractionStatus!=='ready'||doc.extractedText!==(await fs.readFile(path.join(dir,item.path),'utf8')).trim())throw Error(`Missing/truncated input ${item.id}`);
  }
  if(initial.incident.description.replace(/\r\n/g,'\n')!==description.replace(/\r\n/g,'\n'))throw Error('Incident description mismatch');
  await save('frozen-rca-input.json',{incidentId,trackId,model,description:initial.incident.description,documents:docs,answers:[],previousVersion:null});
  await save('initialize-dispatch.json',{incidentId,trackId,at:new Date().toISOString(),inputSha256:sha(await fs.readFile(path.join(dir,'frozen-rca-input.json')))});
  console.log(JSON.stringify({event:'initializing-once',incidentId,trackId,documents:docs.length}));
  const initialized=await request(`/api/tracks/${trackId}/initialize`,{method:'POST',long:true});
  await save('initialize-response.json',initialized);
  const finished=await request(`/api/incidents/${incidentId}`);await save('after-initialize.json',finished);
  const finalTrack=finished.incident.tracks[0];
  if(finalTrack.versions.length!==1||finalTrack.versions[0].number!==1)throw Error('Exactly one V1 was required');
  const version=finalTrack.versions[0];await save('version-1.json',version);
  const analysis=version.analysis;
  await save('question-export.json',{case_id:'IA-16036',run_id:path.basename(dir),incident_id:incidentId,model_track_id:trackId,model_tag:model.name,model_digest:model.digest,board_version:1,input_payload_sha256:sha(await fs.readFile(path.join(dir,'frozen-rca-input.json'))),baselineQuestions:analysis.baselineQuestions,questions:analysis.questions,skippedQuestions:analysis.skippedQuestions,specialistQuestionCheckpoints:finalTrack.checkpoints.filter(c=>c.payload?.questions)});
  if(analysis.stageErrors.length)throw Error('Committed analysis reports failed stages');
  const result={status:'completed_stopped_after_v1',completedAt:new Date().toISOString(),incidentId,trackId,url:`${base}/incident/${incidentId}`,nodes:analysis.causalBoard.nodes.length,edges:analysis.causalBoard.edges.length,questions:analysis.questions.length,storytellerInvoked:false,laterEvidenceReleased:false};
  await save('result.json',result);console.log(JSON.stringify(result));
}catch(error){
  if(incidentId)try{await save(prepared?'analysis-failure-snapshot.json':'failure-snapshot.json',await request(`/api/incidents/${incidentId}`));}catch{}
  const failure={status:'stopped_no_retry',incidentId,trackId,error:String(error),cause:error?.cause ? {message:String(error.cause),code:error.cause.code} : null,at:new Date().toISOString()};await save(prepared?'analysis-failure.json':'failure.json',failure);console.error(JSON.stringify(failure));process.exitCode=1;
}
