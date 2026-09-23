// Explicit one-step operator commands. Story generation never dispatches RCA.
// All live mutations go through the app; never native-write its SQLite database.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {request} from 'node:http';
const root=path.resolve(import.meta.dirname,'..');
const dir=path.join(root,'evals/ia16036-v2-controlled');
const packageRoot=path.resolve(root,'../IA-16036 Controlled Evidence Package/07_case_content_inputs');
const base='http://127.0.0.1:3016';
const incidentId='9660f4f2-5fc0-4d0a-917e-8e48641956e3',trackId='a6647fe7-b418-4232-817f-b3c6d3a5325d';
const v1Id='a20904da-8710-40df-8d58-fec78f451f2a';
const questionIds=['e7f325e3-4bfc-49c7-af57-54661b16b3b6','00af67c6-51bd-4b01-9435-364973e59a91'];
const sha=v=>createHash('sha256').update(v).digest('hex');
const read=name=>fs.readFile(path.join(dir,name),'utf8').then(JSON.parse);
const save=(name,data)=>fs.writeFile(path.join(dir,name),JSON.stringify(data,null,2)+'\n',{flag:'wx'});
async function api(route,body){
  return new Promise((resolve,reject)=>{
    const r=request(base+route,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'content-type':'application/json'}},res=>{
      let raw='';res.setEncoding('utf8');res.on('data',chunk=>raw+=chunk);res.on('error',reject);
      res.on('end',()=>{try{const value=JSON.parse(raw);if((res.statusCode||500)>=400||value.error)throw Error(`${route}: ${value.error||res.statusCode}`);resolve(value);}catch(error){reject(error);}});
    });r.on('error',reject);r.end(body===undefined?undefined:JSON.stringify(body));
  });
}
const storyRoute=`/api/tracks/${trackId}/story`;
async function current(){const incident=(await api(`/api/incidents/${incidentId}`)).incident;return {incident,track:incident.tracks.find(t=>t.id===trackId)};}
async function unchangedV1(track){const before=await read('before.json');if(sha(JSON.stringify(track.versions.find(v=>v.number===1)))!==before.v1Sha256)throw Error('V1 changed.');}
const mode=process.argv[2];
if(mode==='prepare'){
  await fs.mkdir(dir,{recursive:true});
  const {incident,track}=await current();
  if(track.versions.length!==1||track.versions[0].id!==v1Id||!['partial','completed'].includes(track.versions[0].executionStatus))throw Error('Expected published V1 only.');
  const workspace=await api(storyRoute);
  if(workspace.scenario||workspace.rounds.length)throw Error('Existing story world/round: inspect it, do not duplicate.');
  if(questionIds.some(id=>!workspace.questions.some(q=>q.id===id)))throw Error('Question selection changed.');
  const manifest=JSON.parse(await fs.readFile(path.join(packageRoot,'package_manifest.json'),'utf8'));
  const records=await Promise.all(manifest.records.map(async r=>{
    if(!r.path.startsWith('02_model_visible/')&&!r.path.startsWith('04_challenge_evidence/'))throw Error('Non-record path.');
    const text=await fs.readFile(path.join(packageRoot,r.path),'utf8');
    if(sha(text)!==r.sha256)throw Error('Changed record '+r.id);return {...r,text};
  }));
  const sourceIds=records.filter(r=>['B0','B1'].includes(r.release)||['IA-P04','IA-P05'].includes(r.id)).map(r=>r.id);
  const scenario={title:'IA-16036 locked evidence archive',releaseFormat:'case-content',
    hiddenTruth:'The immutable case records define this world. Missing facts remain unknown. Later records require a separate explicit release; no evaluation answer key is provided.',
    sources:records.map(r=>({id:r.id,title:r.text.split('\n')[0].replace(/^#\s*/,''),text:r.text,sourceClass:r.id.startsWith('IA-C')?'Attributed account or retained sheet':'Case record',available:true}))};
  await save('before.json',{at:new Date().toISOString(),incident,track,v1Sha256:sha(JSON.stringify(track.versions[0]))});
  await save('scenario.json',scenario);
  await save('manifest.json',{at:new Date().toISOString(),incidentId,trackId,v1Id,questionIds,sourceIds,
    expectedModelDigest:'6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7',
    newDocumentIds:['IA-P04','IA-P05'],records:records.map(r=>Object.fromEntries(Object.entries(r).filter(([key])=>key!=='text'))),
    expectationsSha256:sha(await fs.readFile(path.join(root,'evals/ia16036-v2-expectations.md'))),
    scenarioSha256:sha(JSON.stringify(scenario)),storyOnly:true});
  console.log(JSON.stringify({prepared:dir,questions:workspace.questions.filter(q=>questionIds.includes(q.id)),sourceIds,newDocuments:['IA-P04','IA-P05']}));
}else if(mode==='create'){
  const {track}=await current();await unchangedV1(track);
  const workspace=await api(storyRoute);if(workspace.scenario)throw Error('Already created; inspect instead of repeating.');
  const scenario=await read('scenario.json');
  const result=await api(storyRoute,{action:'create',scenario});await save('scenario-created.json',result);console.log(result);
}else if(mode==='generate'){
  const manifest=await read('manifest.json');const {track}=await current();await unchangedV1(track);
  const workspace=await api(storyRoute);if(workspace.rounds.length)throw Error('A round already exists; inspect it.');
  await save('story-dispatch.json',{at:new Date().toISOString(),questionIds,sourceIds:manifest.sourceIds});
  const result=await api(storyRoute,{action:'generate',questionIds,sourceIds:manifest.sourceIds});await save('story-generated.json',result);console.log(result);
}else if(mode==='status'){
  const workspace=await api(storyRoute);
  console.log(JSON.stringify({version:workspace.version,rounds:workspace.rounds.map(r=>({id:r.id,status:r.status,updatedAt:r.updated_at,error:r.error,output:r.output}))},null,2));
}else if(mode==='answer'){
  const generated=await read('story-generated.json');
  // One explicit round only. No generation retries, new batches, or RCA dispatch.
  await save('story-work-started.json',{at:new Date().toISOString(),roundId:generated.id});
  for(;;){
    const round=(await api(storyRoute)).rounds.find(r=>r.id===generated.id);
    if(round?.status!=='generating'){console.log(JSON.stringify({status:round?.status,error:round?.error}));break;}
    const result=await api(storyRoute,{action:'step',roundId:generated.id});console.log(JSON.stringify(result));
    if(result.idle||result.leaseLost)throw Error('Round did not acquire work; inspect its lease before retrying.');
  }
}else if(mode==='freeze'){
  const workspace=await api(storyRoute);const round=workspace.rounds.find(r=>r.base_version===1);
  if(round?.status!=='ready'||round.output.output.answers.length!==2)throw Error('Complete two-answer batch not ready.');
  await save('story-candidate.json',{at:new Date().toISOString(),round,outputSha256:sha(JSON.stringify(round.output.output))});
  console.log(JSON.stringify({roundId:round.id,outputSha256:sha(JSON.stringify(round.output.output)),answers:round.output.output.answers},null,2));
}else if(mode==='apply'){
  const candidate=await read('story-candidate.json'),review=await read('story-review.json');
  if(!['release-unedited','release-reviewed-subset-unedited'].includes(review.decision)||review.outputSha256!==candidate.outputSha256)throw Error('Expected explicit review of exact batch.');
  const {track}=await current();await unchangedV1(track);if(track.versions.length!==1)throw Error('V2 already exists; do not dispatch again.');
  const round=(await api(storyRoute)).rounds.find(r=>r.id===candidate.round.id);
  if(round?.status!=='ready'||sha(JSON.stringify(round.output.output))!==candidate.outputSha256)throw Error('Batch changed.');
  const documents=[{sourceId:'IA-P04',questionId:questionIds[0]},{sourceId:'IA-P05',questionId:questionIds[1]}];
  await save('v2-dispatch.json',{at:new Date().toISOString(),roundId:round.id,documents,storyOutputSha256:candidate.outputSha256,approvedQuestionIds:review.approvedQuestionIds});
  const result=await api(storyRoute,{action:'apply',roundId:round.id,documents,approvedQuestionIds:review.approvedQuestionIds});await save('v2-enqueued.json',result);console.log(result);
}else if(mode==='result'){
  const {incident,track}=await current();await unchangedV1(track);
  const v2=track.versions.find(v=>v.number===2);
  console.log(JSON.stringify({at:new Date().toISOString(),v1Unchanged:true,versions:track.versions.map(v=>({id:v.id,number:v.number,status:v.executionStatus})),
    progress:v2?.analysis.engineProgress,position:v2?.analysis.investigationPosition?.stage,
    nodes:v2?.analysis.causalBoard.nodes.length,edges:v2?.analysis.causalBoard.edges.length},null,2));
  if(v2&&['completed','partial'].includes(v2.executionStatus))await save('v2-result.json',{at:new Date().toISOString(),incident,track});
}else throw Error('Use prepare, create, generate, answer, status, freeze, apply or result.');
