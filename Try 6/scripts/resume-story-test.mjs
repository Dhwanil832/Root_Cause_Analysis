import './legacy-disabled.mjs';
import fs from 'node:fs/promises';
import {spawn} from 'node:child_process';
const incidentId='5d41662f-9b61-46a7-8ef7-5cb79c127271',trackId='12a72d40-6c90-4bf3-9566-82fa9563d014';
const base='http://localhost:3000',endpoint=`${base}/api/tracks/${trackId}/story`;
const dir=await fs.mkdtemp('/Users/dhwanilchauhan/Desktop/RCA Try 1/R3 Benchmark Package/06_run_records/qwen-story-resume-');
const save=(name,data)=>fs.writeFile(`${dir}/${name}.json`,JSON.stringify(data,null,2));
async function call(url,body){
 const child=spawn('/usr/bin/curl',['-sS','--max-time','14400',url,...(body?['-H','Content-Type: application/json','--data-binary','@-']:[])]);let out='';
 child.stdout.on('data',x=>out+=x);child.stderr.on('data',x=>process.stderr.write(x));child.stdin.end(body?JSON.stringify(body):undefined);
 const code=await new Promise(r=>child.on('close',r));if(code)throw Error(`Transport failure ${code}; inspect saved state before retrying.`);
 const d=JSON.parse(out);if(d.error)throw Error(d.error);return d;
}
const timer=setInterval(()=>console.log(new Date().toISOString(),'active',trackId),60000);
try{
 console.log('Artifacts:',dir);
 await save('protocol',{incidentId,trackId,note:'Preserve failed V1. Resume unanswered questions with storyteller; V2 reruns RCA with released evidence. Provider now passes JSON parse errors to same-model repair attempt. No model substitution.'});
 for(;;){
  const incident=(await call(`${base}/api/incidents/${incidentId}`)).incident;
  const version=incident.tracks.find(t=>t.id===trackId).versions.at(-1);
  await save(`version-${version.number}`,version);
  if(version.number>=5){console.log('Target V5 reached');break;}
  // The original failed V1 remains visible; later failures require operator inspection.
  if(version.number>1&&version.analysis.stageErrors?.length)throw Error('New RCA cycle has stage errors; inspect before continuing.');
  let w=await call(endpoint);
  if(!w.questions.length){console.log('No new pending questions');break;}
  let round=w.rounds.find(r=>r.base_version===version.number);
  if(round&&['generating','applying'].includes(round.status))throw Error('An existing round is active; refusing duplicate execution.');
  if(!round||round.status==='failed'){await call(endpoint,{action:'generate'});w=await call(endpoint);round=w.rounds.find(r=>r.base_version===version.number);}
  await save(`story-after-v${version.number}`,w);
  if(round?.status!=='ready')throw Error('Round is not ready.');
  console.log('Applying story batch after V'+version.number);
  await call(endpoint,{action:'apply',roundId:round.id});
 }
 await save('result',{status:'finished',incidentId,trackId});
}catch(e){await save('failure',{error:String(e),incidentId,trackId});console.error(String(e));process.exitCode=1;}finally{clearInterval(timer);}
