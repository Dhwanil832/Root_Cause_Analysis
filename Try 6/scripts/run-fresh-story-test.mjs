import './legacy-disabled.mjs';
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
const base='http://localhost:3000';
const root='/Users/dhwanilchauhan/Desktop/RCA Try 1/R3 Benchmark Package';
const dir=await fs.mkdtemp(path.join(root,'06_run_records/qwen-story-fresh-'));
const save=(name,value)=>fs.writeFile(path.join(dir,name),JSON.stringify(value,null,2));
async function request(url,body){
  const args=['-sS','--max-time','14400',url];
  if(body)args.push('-H','Content-Type: application/json','--data-binary','@-');
  const child=spawn('/usr/bin/curl',args);let out='',err='';
  child.stdout.on('data',x=>out+=x);child.stderr.on('data',x=>err+=x);
  if(body)child.stdin.end(JSON.stringify(body));else child.stdin.end();
  const code=await new Promise(r=>child.on('close',r));
  if(code)throw Error(`Request failed (${code}): ${err}`);
  const data=JSON.parse(out);if(data.error)throw Error(data.error);return data;
}
let incidentId,trackId;
const heartbeat=setInterval(()=>console.log(JSON.stringify({time:new Date().toISOString(),incidentId,trackId,status:'running'})),60000);
try{
  const description=await fs.readFile(path.join(root,'02_model_visible/00_incident_input/incident_summary.txt'),'utf8');
  const starters=['Initial_Evidence_Register.pdf','Initial_Scene_Sketch_and_Timeline.pdf','Preliminary_Incident_Notification_16515.pdf'];
  const references=await request(base+'/api/references');
  await save('initial-references.json',references);
  await save('manifest.json',{startedAt:new Date().toISOString(),model:'ollama:qwen3.5:latest',targetVersions:5,description,starters,mode:'Fresh progressive disclosure; same-model isolated storyteller; automatic release for this authorized test'});
  console.log('Run artifacts: '+dir);
  const args=['-sS','--max-time','14400',base+'/api/incidents','--form',`description=<${path.join(root,'02_model_visible/00_incident_input/incident_summary.txt')}`,'--form','modelIds=["ollama:qwen3.5:latest"]'];
  for(const name of starters)args.push('--form',`files=@${path.join(root,'02_model_visible/02_starter_documents',name)};type=application/pdf`);
  const child=spawn('/usr/bin/curl',args);let out='';child.stdout.on('data',x=>out+=x);child.stderr.on('data',x=>process.stderr.write(x));
  const code=await new Promise(r=>child.on('close',r));if(code)throw Error(`Create transport failure ${code}; do not retry blindly—inspect history.`);
  const created=JSON.parse(out);if(created.error)throw Error(created.error);incidentId=created.id;
  let incident=(await request(`${base}/api/incidents/${incidentId}`)).incident;
  trackId=incident.tracks[0].id;
  await save('identity.json',{incidentId,trackId,url:`${base}/incident/${incidentId}`});
  const endpoint=`${base}/api/tracks/${trackId}/story`;
  const scenario=await request(base+'/api/story-template');
  await save('private-story-scenario.json',scenario);
  await request(endpoint,{action:'create',scenario});
  for(let number=1;number<=5;number++){
    incident=(await request(`${base}/api/incidents/${incidentId}`)).incident;
    const version=incident.tracks[0].versions.at(-1);
    await save(`version-${version.number}.json`,version);
    console.log(JSON.stringify({version:version.number,nodes:version.analysis.causalBoard.nodes.length,edges:version.analysis.causalBoard.edges.length,errors:version.analysis.stageErrors}));
    if(version.analysis.stageErrors?.length)throw Error('RCA stage errors: stopping; partial version retained.');
    if(number===5)break;
    let workspace=await request(endpoint);
    if(!workspace.questions.length){console.log('No pending questions; stopping.');break;}
    await request(endpoint,{action:'generate'});
    workspace=await request(endpoint);
    await save(`story-after-v${number}.json`,workspace);
    const round=workspace.rounds.find(r=>r.base_version===number);
    if(round?.status!=='ready')throw Error('Story round not ready; no batch released.');
    await request(endpoint,{action:'apply',roundId:round.id});
  }
  await save('result.json',{status:'complete',incidentId,trackId,completedAt:new Date().toISOString()});
  console.log('COMPLETE '+`${base}/incident/${incidentId}`);
}catch(error){await save('failure.json',{error:String(error),incidentId,trackId,at:new Date().toISOString()});console.error(String(error));process.exitCode=1;}
finally{clearInterval(heartbeat);}
