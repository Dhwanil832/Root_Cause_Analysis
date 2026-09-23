import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';

const runDir = path.dirname(fileURLToPath(import.meta.url));
const pkg = path.resolve(runDir, '../..');
const app = 'http://localhost:3000';
const model = 'ollama:qwen3.5:latest';
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const stamp = () => new Date().toISOString().replace(/[:.]/g, '-');
async function save(name, data) { await fs.writeFile(path.join(runDir, name), typeof data === 'string' ? data : JSON.stringify(data, null, 2)); }
async function event(kind, data={}) { const row={at:new Date().toISOString(), kind,...data}; await fs.appendFile(path.join(runDir,'events.jsonl'), JSON.stringify(row)+'\n'); console.log(JSON.stringify(row)); }
async function walk(dir) { const out=[]; for(const e of await fs.readdir(dir,{withFileTypes:true})) { const p=path.join(dir,e.name); if(e.isDirectory()) out.push(...await walk(p)); else out.push(p); } return out; }
async function request(label, method, endpoint, extra=[]) {
  const key = `${stamp()}-${label}`;
  const args=['--silent','--show-error','--max-time','14400','--request',method,app+endpoint,...extra,'--write-out','\n%{http_code}'];
  await save(`requests/${key}.json`,{at:new Date().toISOString(),method,endpoint,args});
  await event('http-request',{key,method,endpoint});
  const child=spawn('/usr/bin/curl',args,{stdio:['ignore','pipe','pipe']});
  let stdout='',stderr='';child.stdout.on('data',b=>stdout+=b);child.stderr.on('data',b=>stderr+=b);
  const code=await new Promise((resolve,reject)=>{child.on('error',reject);child.on('close',resolve);});
  const split=stdout.lastIndexOf('\n');const body=stdout.slice(0,split);const status=Number(stdout.slice(split+1));
  await save(`responses/${key}.body`,body);await save(`responses/${key}.meta.json`,{code,status,stderr,sha256:sha(body)});
  let payload;try{payload=JSON.parse(body)}catch{payload={raw:body}}
  await event('http-response',{key,code,status,sha256:sha(body)});
  if(code!==0||status<200||status>299)throw new Error(`Request ${key}: curl ${code}, HTTP ${status}, ${stderr}, ${body.slice(0,1000)}. Inspect saved checkpoints before retry.`);
  return payload;
}
async function snapshot(id,label='snapshot') {
  const result=await request(label,'GET',`/api/incidents/${id}`);
  const item=result.incident; if(!item) throw new Error('Incident absent in API response');
  await save(`snapshots/${stamp()}-${label}.json`,result);
  const track=item.tracks[0];const version=track?.versions.at(-1);
  if(version){
    await save(`version-${version.number}.json`,version);
    const a=version.analysis;
    await save(`questions-version-${version.number}.json`,{baselineQuestions:a.baselineQuestions,canonicalQuestions:a.questions,skippedQuestions:a.skippedQuestions,verificationFindings:a.causalBoard.verificationFindings,answerFetches:a.answerFetches,answers:a.answers});
  }
  await event('snapshot',{id,trackId:track?.id,versions:track?.versions.length,latestVersion:version?.number,checkpoints:track?.checkpoints?.length,lastCheckpoint:track?.checkpoints?.at(-1)?.stage,status:version?.analysis.status});
  return result;
}
async function init() {
  for(const d of ['requests','responses','snapshots','releases','qa'])await fs.mkdir(path.join(runDir,d),{recursive:true});
  const paths=[];for(const d of ['01_withheld_ground_truth','02_model_visible','03_answer_bank','04_challenge_evidence'])paths.push(...await walk(path.join(pkg,d)));
  const inventory=[];for(const p of paths){const b=await fs.readFile(p);inventory.push({path:path.relative(pkg,p),bytes:b.length,sha256:sha(b),modelVisibility:p.includes('/01_withheld_ground_truth/')||p.includes('/03_answer_bank/')||p.endsWith('/README.md')?'never-wholesale':'conditional'});}
  await save('evidence-inventory.json',{frozenAt:new Date().toISOString(),files:inventory});
  const refs=await request('phase0-references','GET','/api/references');await save('phase0-reference-inventory.json',refs);
  const models=await request('phase0-models','GET','/api/models');await save('phase0-models.json',models);
  const history=await request('phase0-history','GET','/api/incidents');await save('phase0-history.json',history);
  await event('prepared',{runDir,app,model,files:inventory.length});
}
async function create(){
  await fs.access(path.join(runDir,'evidence-inventory.json'));await fs.access(path.join(runDir,'phase0-reference-inventory.json'));
  const description=path.join(pkg,'02_model_visible/00_incident_input/incident_summary.txt');
  const files=(await fs.readdir(path.join(pkg,'02_model_visible/02_starter_documents'))).filter(f=>f.endsWith('.pdf')).sort().map(f=>path.join(pkg,'02_model_visible/02_starter_documents',f));
  if(files.length!==3)throw new Error('Expected exactly 3 starter documents');
  const args=['--form',`description=<${description}`,'--form',`modelIds=${JSON.stringify([model])}`];for(const f of files)args.push('--form',`files=@${f};type=application/pdf`);
  await save('creation-input.json',{model,descriptionSha256:sha(await fs.readFile(description)),files:await Promise.all(files.map(async p=>({path:path.relative(pkg,p),sha256:sha(await fs.readFile(p))}))),withheldSupplied:false});
  const response=await request('create','POST','/api/incidents',args);await save('create-response.json',response);await snapshot(response.id,'creation-complete');
}
async function discover(){
  const base=JSON.parse(await fs.readFile(path.join(runDir,'phase0-history.json'),'utf8'));const old=new Set(base.incidents.map(i=>i.id));
  const now=await request('discover','GET','/api/incidents');const fresh=now.incidents.filter(i=>!old.has(i.id));
  await save('discovered-incidents.json',fresh);console.log(JSON.stringify(fresh));
  if(fresh.length===1){const result=await snapshot(fresh[0].id,'discovered');await save('identity.json',{incidentId:fresh[0].id,trackId:result.incident.tracks[0]?.id,appUrl:app,incidentUrl:`${app}/incident/${fresh[0].id}`});}
}
async function upload(fileArg,questionId){
 const id=JSON.parse(await fs.readFile(path.join(runDir,'identity.json'),'utf8'));const file=path.resolve(fileArg);const body=await fs.readFile(file);
 const rel=path.relative(pkg,file);if(rel.startsWith('01_withheld_ground_truth')||rel.startsWith('03_answer_bank')||rel.startsWith('05_evaluation'))throw new Error('Forbidden upload');
 if(!(file.includes('/02_model_visible/')||file.includes('/04_challenge_evidence/')||file.startsWith(path.join(runDir,'releases')+'/')))throw new Error('Upload outside approved evidence locations');
 await event('source-release',{questionId,path:rel,sha256:sha(body)});
 const type=file.endsWith('.pdf')?'application/pdf':file.endsWith('.md')?'text/markdown':'text/plain';
 const response=await request('upload','POST','/api/uploads',['--form',`file=@${file};type=${type}`,'--form',`trackId=${id.trackId}`,'--form',`questionId=${questionId}`]);
 await save(`qa/upload-${path.basename(file)}.json`,response);console.log(JSON.stringify({documentId:response.document?.id,fileKey:response.fileKey,fileName:response.fileName}));
}
async function answer(fileArg){
 const id=JSON.parse(await fs.readFile(path.join(runDir,'identity.json'),'utf8'));const f=path.resolve(fileArg);const data=JSON.parse(await fs.readFile(f,'utf8'));
 if(!data.questionId||!data.answer)throw new Error('Missing question/answer');
 const before=await snapshot(id.incidentId,'before-answer');const a=before.incident.tracks[0].versions.at(-1).analysis;
 const actual=[...a.questions,...a.baselineQuestions].find(q=>q.id===data.questionId);
 if(!actual)throw new Error('Question ID not in current actual question sets');
 await save(`qa/${stamp()}-submission-context.json`,{actual,answerFetch:a.answerFetches.filter(f=>f.questionId===data.questionId),skipped:a.skippedQuestions.filter(q=>q.coveredByQuestionId===data.questionId),body:data,bodySha256:sha(await fs.readFile(f))});
 const result=await request('answer','POST',`/api/tracks/${id.trackId}/versions`,['--header','Content-Type: application/json','--data-binary',`@${f}`]);await save(`response-version-${result.version}.json`,result);await snapshot(id.incidentId,'answer-complete');
}
const [cmd,...rest]=process.argv.slice(2);
try{if(cmd==='init')await init();else if(cmd==='create')await create();else if(cmd==='discover')await discover();else if(cmd==='snapshot'){const id=JSON.parse(await fs.readFile(path.join(runDir,'identity.json'),'utf8'));await snapshot(id.incidentId,rest[0]||'snapshot');}else if(cmd==='upload')await upload(...rest);else if(cmd==='answer')await answer(...rest);else throw new Error('Use init/create/discover/snapshot/upload/answer');}catch(e){await event('error',{cmd,error:String(e),stack:e.stack});process.exitCode=1;}
