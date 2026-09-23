import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';

// Operator-side package adapter only. Never part of a model prompt or retrieval.
const packageDir=path.resolve(process.argv[2]||'../IA-16036 Controlled Evidence Package');
const base=process.env.RCA_APP_URL||'http://127.0.0.1:3015';
const model='ollama:qwen3.5:latest';
const manifest=JSON.parse(await fs.readFile(path.join(packageDir,'package_manifest.json'),'utf8'));
const records=await Promise.all(manifest.records.filter(r=>r.release==='B0').map(async r=>{
  if(!r.path.startsWith('02_model_visible/'))throw Error('Refusing non-model-visible evidence');
  const data=await fs.readFile(path.join(packageDir,r.path));return {...r,data,sha256:createHash('sha256').update(data).digest('hex')};
}));
async function api(route,options){const r=await fetch(base+route,options),data=await r.json();if(!r.ok)throw Error(JSON.stringify(data));return data;}
const references=(await api('/api/references')).documents;
const intended=records.filter(r=>r.scope==='default_reference');
if(references.length!==intended.length||references.some(d=>!intended.some(r=>r.sha256===d.sha256)||d.extractionStatus!=='ready'))
  throw Error('Reference library differs from frozen B0 package. Do not start inference.');
const summary=records.find(r=>r.scope==='incident_description');
const form=new FormData();form.set('description',summary.data.toString('utf8'));form.set('modelIds',JSON.stringify([model]));form.set('deferAnalysis','true');
form.set('title',`${manifest.case_id} · Try 5.2.1 controlled Qwen · B0 · ${new Date().toISOString()}`);
for(const r of records.filter(r=>r.scope==='starter_document'))form.append('files',new File([r.data],path.basename(r.path),{type:'text/markdown'}));
const created=await api('/api/incidents',{method:'POST',body:form});
// Print identity immediately so a later verification failure cannot hide a draft.
console.log(JSON.stringify({createdIncident:created.id,deferred:true}));
const {incident}=await api(`/api/incidents/${created.id}`),track=incident.tracks[0];
if(incident.tracks.length!==1||track.modelId!==model||track.versions.length)throw Error('Unexpected track or premature inference');
const documents=records.filter(r=>r.scope!=='incident_description');
if(track.documents.length!==documents.length||track.documents.some(d=>!documents.some(r=>r.sha256===d.sha256)||d.extractionStatus!=='ready'))
  throw Error('Attached evidence does not match the frozen package. Draft preserved; no inference started.');
const initialized=await api(`/api/tracks/${track.id}/initialize`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({reviewAfterReading:true})});
if(initialized.reviewAfterReading!==true){await api(`/api/tracks/${track.id}/pause`,{method:'POST'});throw Error('Checkpoint policy was not acknowledged. Paused before proceeding.');}
console.log(JSON.stringify({launchedAt:new Date().toISOString(),incidentId:created.id,trackId:track.id,model,engine:initialized.engineVersion,release:'B0',
  dashboard:`${base}/incident/${created.id}`,initialized,inputs:records.map(({id,scope,sha256})=>({id,scope,sha256}))},null,2));
