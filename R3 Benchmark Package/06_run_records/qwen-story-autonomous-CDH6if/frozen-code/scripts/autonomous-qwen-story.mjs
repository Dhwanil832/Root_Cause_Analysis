import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {causalCommitProblems} from '../src/orchestrator/commit-contract.ts';

const app=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const benchmark=path.resolve(app,'../R3 Benchmark Package');
const dir=process.argv[process.argv.indexOf('--run-dir')+1];
if(!process.argv.includes('--run-dir') || !path.isAbsolute(dir)) throw Error('An explicit absolute --run-dir is required.');
const option=(name,fallback)=>process.argv.includes(name)?process.argv[process.argv.indexOf(name)+1]:fallback;
const base=option('--base-url','http://localhost:3000');
const ollamaBase=option('--ollama-url','http://127.0.0.1:11434');
for(const url of [base,ollamaBase])if(!['localhost','127.0.0.1','[::1]'].includes(new URL(url).hostname))throw Error('Only local services are permitted.');
const model='ollama:qwen3.5:latest',target=4;
const started=Date.now(),deadline=started+24*60*60*1000;
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const canonical=value=>JSON.stringify(value,(_key,item)=>item&&typeof item==='object'&&!Array.isArray(item)
  ? Object.fromEntries(Object.entries(item).sort(([a],[b])=>a.localeCompare(b))) : item);
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const state={status:'preparing',pid:process.pid,model,targetVersions:target,committedVersions:0,startedAt:new Date().toISOString()};
let frozen={},requestNumber=0;
await fs.mkdir(path.join(dir,'requests'),{recursive:true});
const lock=await fs.open(path.join(dir,'runner.lock'),'wx');
await lock.writeFile(JSON.stringify({pid:process.pid,startedAt:state.startedAt}));
await lock.close();
async function save(name,value){
  const destination=path.join(dir,name),temporary=destination+'.pending';
  await fs.writeFile(temporary,JSON.stringify(value,null,2));
  await fs.rename(temporary,destination);
}
async function progress(phase,extra={}){
  Object.assign(state,{phase,updatedAt:new Date().toISOString()},extra);
  await save('state.json',state);
  await fs.appendFile(path.join(dir,'events.jsonl'),JSON.stringify({at:state.updatedAt,phase,...extra})+'\n');
  console.log(JSON.stringify({at:state.updatedAt,phase,...extra}));
}
async function immutable(name,value){
  const serialized=JSON.stringify(value,null,2),file=path.join(dir,name);
  try {await fs.writeFile(file,serialized,{flag:'wx'});}
  catch(error){if(error.code!=='EEXIST')throw error;if(await fs.readFile(file,'utf8')!==serialized)throw Error(`Immutable artifact changed: ${name}`);}
}
async function call(endpoint,body,formFiles){
  if(Date.now()>deadline)throw Error('24-hour safety deadline reached; no further requests dispatched.');
  const key=String(++requestNumber).padStart(4,'0');
  await save(`requests/${key}-request.json`,{endpoint,body:body||null,formFiles:formFiles||null,at:new Date().toISOString()});
  const args=['-sS','--max-time','21600','--write-out','\n%{http_code}',base+endpoint];
  if(formFiles){
    for(const [field,value] of Object.entries(body)) args.push('--form-string',`${field}=${value}`);
    for(const file of formFiles)args.push('--form',`files=@${file};type=application/pdf`);
  }else if(body)args.push('-H','Content-Type: application/json','--data-binary','@-');
  const child=spawn('/usr/bin/curl',args);let out='',stderr='';
  child.stdout.on('data',chunk=>out+=chunk);child.stderr.on('data',chunk=>stderr+=chunk);
  child.stdin.end(body&&!formFiles?JSON.stringify(body):undefined);
  const code=await new Promise((resolve,reject)=>{child.on('close',resolve);child.on('error',reject);});
  const split=out.lastIndexOf('\n'),httpStatus=Number(out.slice(split+1)),raw=out.slice(0,split);
  await fs.writeFile(path.join(dir,`requests/${key}-response.txt`),out);
  if(code)throw Object.assign(Error(`Uncertain transport result (${code}): ${stderr}. Do not repeat a mutation blindly.`),{uncertain:true});
  let data;try{data=JSON.parse(raw);}catch{throw Object.assign(Error(`Non-JSON HTTP ${httpStatus}; inspect request ${key}.`),{uncertain:true});}
  if(httpStatus>=400||data.error)throw Error(data.error||`HTTP ${httpStatus}`);
  return data;
}
async function sourceFiles(folder){
  const files=[];
  for(const entry of await fs.readdir(path.join(app,folder),{withFileTypes:true})){
    const relative=path.join(folder,entry.name);
    if(entry.isDirectory())files.push(...await sourceFiles(relative));
    else if(entry.isFile()&&/\.(ts|tsx|mjs|md|json)$/.test(entry.name))files.push(relative);
  }
  return files;
}
async function freezeCode(){
  const files=['package.json',...await sourceFiles('src'),...await sourceFiles('prompts'),...await sourceFiles('app/api'),
    'scripts/autonomous-qwen-story.mjs','scripts/launch-qwen-story.mjs'];
  for(const relative of files){
    const bytes=await fs.readFile(path.join(app,relative));frozen[relative]=sha(bytes);
    const destination=path.join(dir,'frozen-code',relative);await fs.mkdir(path.dirname(destination),{recursive:true});await fs.writeFile(destination,bytes);
  }
  await save('code-hashes.json',frozen);
}
async function assertCodeUnchanged(){
  for(const [relative,hash] of Object.entries(frozen))if(sha(await fs.readFile(path.join(app,relative)))!==hash)throw Error(`Code/prompt changed during the experiment: ${relative}. Stopped to preserve comparability.`);
}
async function snapshot(){
  const response=await call(`/api/incidents/${state.incidentId}`);
  const track=response.incident.tracks.find(track=>track.id===state.trackId);
  if(!track||track.modelId!==model||response.incident.tracks.length!==1)throw Error('Expected exactly one isolated Qwen track.');
  await save('latest-incident.json',response);
  for(const version of track.versions)await immutable(`version-${version.number}.json`,version);
  state.committedVersions=track.versions.length;
  return track;
}
async function mutationWithRecovery(endpoint,body,isComplete,maxAttempts=1){
  for(let attempt=1;attempt<=maxAttempts;attempt++){
    await assertCodeUnchanged();
    try{return await call(endpoint,body);}
    catch(error){
      await progress('request-failed',{lastError:String(error),requestAttempt:attempt});
      // Read the committed state before even considering a retry.
      if(await isComplete())return;
      if(error.uncertain||attempt===maxAttempts)throw error;
      await sleep(3000);
    }
  }
}
let timer;
try{
  await freezeCode();
  const description=await fs.readFile(path.join(benchmark,'02_model_visible/00_incident_input/incident_summary.txt'),'utf8');
  const title=`R3 — Qwen storyteller · unattended ${new Date().toISOString()}`;
  const starterNames=['Initial_Evidence_Register.pdf','Initial_Scene_Sketch_and_Timeline.pdf','Preliminary_Incident_Notification_16515.pdf'];
  const starters=starterNames.map(name=>path.join(benchmark,'02_model_visible/02_starter_documents',name));
  const references=await call('/api/references');
  const history=await call('/api/incidents');
  await save('references-before.json',references);await save('history-before.json',history);
  const originalVersions={};
  for(const previous of history.incidents){
    const response=await call(`/api/incidents/${previous.id}`);
    for(const track of response.incident.tracks)for(const version of track.versions)originalVersions[version.id]=sha(JSON.stringify(version));
  }
  await save('prior-version-hashes.json',originalVersions);
  const tags=await new Promise((resolve,reject)=>{
    const child=spawn('/usr/bin/curl',['-sS','--max-time','10',ollamaBase+'/api/tags']);let out='';
    child.stdout.on('data',data=>out+=data);child.on('error',reject);child.on('close',code=>{try{if(code)throw Error('Ollama unavailable');resolve(JSON.parse(out));}catch(error){reject(error);}});
  });
  const installed=tags.models.find(item=>item.name==='qwen3.5:latest');
  if(!installed)throw Error('qwen3.5:latest is not installed. No substitute model will be used.');
  await save('manifest.json',{model,targetVersions:target,title,description,startedAt:state.startedAt,
    installedModel:installed,starterFiles:await Promise.all(starters.map(async file=>({file,sha256:sha(await fs.readFile(file))}))),
    rules:{sameModelOnly:true,humanAnswers:false,automaticRelease:true,strictCausalCommit:true,
      maxFullCyclesPerRequest:1,maxRcaRequestsPerAction:1,maxStoryGenerationRequests:2,deadlineHours:24,
      retryScope:'failed provider stage or broker batch only',
      stopOnEvidenceExhaustion:true,stopOnUncertainMutation:true,promptVersion:'try4.2.1-broker-contract'}});
  await progress('creating-fresh-incident',{status:'running'});
  timer=setInterval(()=>save('heartbeat.json',{at:new Date().toISOString(),pid:process.pid,phase:state.phase,incidentId:state.incidentId,committedVersions:state.committedVersions}).catch(console.error),15000);
  // Creation only stores the incident and inputs; it returns before inference.
  // Never retry this non-idempotent operation after a transport error.
  const created=await call('/api/incidents',{description,modelIds:JSON.stringify([model]),deferAnalysis:'true',title},starters);
  state.incidentId=created.id;
  const incident=(await call(`/api/incidents/${created.id}`)).incident;
  if(incident.tracks.length!==1)throw Error('Unexpected model tracks at creation.');
  state.trackId=incident.tracks[0].id;
  state.url=`${base}/incident/${state.incidentId}`;
  await immutable('identity.json',{incidentId:state.incidentId,trackId:state.trackId,url:state.url,model});
  await progress('initial-causal-analysis');
  await mutationWithRecovery(`/api/tracks/${state.trackId}/initialize`,{},async()=>Boolean((await snapshot()).versions.length));
  const endpoint=`/api/tracks/${state.trackId}/story`;
  const scenario=await call('/api/story-template');
  await immutable('private-story-scenario.json',scenario);
  await call(endpoint,{action:'create',scenario});
  const scenarioHash=sha(canonical(scenario));
  for(;;){
    const track=await snapshot(),version=track.versions.at(-1);
    if(!version)throw Error('No committed initial version.');
    const problems=causalCommitProblems(version.analysis);
    if(problems.length)throw Error(`A committed version is incomplete: ${problems.join('; ')}`);
    if(version.number!==track.versions.length)throw Error('Version sequence is not contiguous.');
    await progress('version-committed',{committedVersions:version.number,lastError:null});
    if(version.number===target)break;
    if(version.number>target)throw Error('Unexpected extra version; stop without modifying history.');
    let workspace=await call(endpoint);
    if(sha(canonical(workspace.scenario.definition))!==scenarioHash)throw Error('The locked story world changed.');
    if(!workspace.questions.length)throw Error('Evidence/questions exhausted before V4. No invented questions or padding versions will be created.');
    await progress('storyteller-answering',{baseVersion:version.number,pendingQuestions:workspace.questions.length});
    await mutationWithRecovery(endpoint,{action:'generate'},async()=>{
      const w=await call(endpoint);await save(`story-after-v${version.number}-recovery.json`,w);
      const round=w.rounds.find(round=>round.base_version===version.number);
      if(round&&['generating','applying'].includes(round.status))throw Error('Story request may still be active; stopped to avoid duplicate execution.');
      return round?.status==='ready'||round?.status==='applied';
    },2);
    workspace=await call(endpoint);await immutable(`story-after-v${version.number}.json`,workspace);
    const round=workspace.rounds.find(round=>round.base_version===version.number);
    if(round?.status!=='ready')throw Error('No validated story batch ready for release.');
    await progress('applying-story-batch',{baseVersion:version.number,storyRoundId:round.id,answerCount:round.output.output.answers.length});
    await mutationWithRecovery(endpoint,{action:'apply',roundId:round.id,strictCausal:true},async()=>{
      const latest=(await snapshot()).versions.at(-1);
      if(latest?.number===version.number+1)return true;
      const w=await call(endpoint),r=w.rounds.find(r=>r.id===round.id);
      if(r?.status==='applying')throw Error('RCA update may still be active; stopped to avoid a duplicate version.');
      return false;
    });
  }
  await assertCodeUnchanged();
  const finalStory=await call(endpoint);await save('final-story-workspace.json',finalStory);
  if(finalStory.rounds.filter(round=>round.status==='applied').length!==3)throw Error('Expected three applied storyteller batches.');
  for(const previous of history.incidents){
    const response=await call(`/api/incidents/${previous.id}`);
    for(const track of response.incident.tracks)for(const version of track.versions)if(originalVersions[version.id]&&originalVersions[version.id]!==sha(JSON.stringify(version)))throw Error(`Prior version was modified: ${version.id}`);
  }
  await progress('four-versions-committed',{status:'complete',completedAt:new Date().toISOString()});
  await save('result.json',{...state,priorVersionsUnchanged:true,analysisPending:true});
}catch(error){
  await progress('stopped',{status:'failed',error:String(error),finishedAt:new Date().toISOString()});
  await save('failure.json',state);process.exitCode=1;
}finally{
  if(timer)clearInterval(timer);
  await fs.unlink(path.join(dir,'runner.lock'));
}
