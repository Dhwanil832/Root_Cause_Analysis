// Offline compatibility/failure-containment check. Replays an unchanged saved
// model answer; makes no inference and must not count as a new semantic pass.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {initializeState} from '../src/engine/tasks/planner.ts';
import {applyEvidenceTask} from '../src/stages/evidence-reading/task.ts';
import {CLAIM_REVIEW_POLICY} from '../src/engine/review/literal-contract.ts';
const [directory,prefix='01']=process.argv.slice(2);
if(!directory)throw Error('Usage: replay-review-failure.mjs SAVED_REVIEW_DIRECTORY [PREFIX]');
const request=JSON.parse(fs.readFileSync(path.join(directory,prefix+'-review-request.json'),'utf8'));
const failure=JSON.parse(fs.readFileSync(path.join(directory,prefix+'-failure.json'),'utf8'));
const raw=failure.output||JSON.parse(failure.attempts[0].raw);
const manifest=JSON.parse(fs.readFileSync(path.join(directory,'manifest.json'),'utf8'));
const state=await initializeState({incident:'Offline failure replay; original request text only.',model:manifest.model,documents:[],answers:[]},1,null);
const refs={sources:new Map(),findings:new Map(),questions:new Map()};
state.sources=request.packet.evidence.map((e,i)=>{
  const id=request.selectedEvidence[i],text=e.text.split('\n').map(line=>line.replace(/^\d+\|/,'')).join('\n');
  refs.sources.set(e.ref,id);
  return {id:'replayed:'+id,revision:'1',label:e.label,textHash:createHash('sha256').update(text).digest('hex'),scope:e.scope,origin:e.origin,limitations:[],
    spans:[{id,sourceId:'replayed:'+id,label:e.label,text,scope:e.scope,origin:e.origin,start:0,end:text.length,heading:e.heading,tableHeader:e.tableHeaderContext}]};
});
const finding={id:'saved-failed-claim',revision:1,statement:request.packet.target.statement,kind:'observation',subject:'work package',predicate:'',location:'',time:'',unit:'',qualifiers:'',
  spanIds:request.selectedEvidence,tags:[],owners:['equipment-tool'],status:'proposed',reviewReason:'',opposedBy:[],history:[],introducedVersion:1,updatedVersion:1};
state.findings.push(finding);
const task={id:'saved-failure-replay',kind:'review',owner:'claim-review',targetIds:[finding.id]};
let error;
try{applyEvidenceTask(state,task,raw,refs);}catch(e){error=e.message;}
const result={policy:CLAIM_REVIEW_POLICY,sourceDirectory:path.resolve(directory),sourcePolicy:manifest.reviewPolicy,
  execution:'Offline replay of unchanged model output against original saved request text. No model call, no application DB, no semantic acceptance credit.',
  error,status:finding.status,reviewExecution:finding.reviewExecution,questions:state.questions,newFacts:state.findings.length-1,
  outputHash:createHash('sha256').update(JSON.stringify(raw)).digest('hex')};
fs.mkdirSync('outputs',{recursive:true});const output=fs.mkdtempSync(path.resolve('outputs/review-gap-replay-'));
fs.writeFileSync(path.join(output,'result.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
if(!error||finding.reviewExecution!=='incomplete'||finding.status!=='proposed'||state.questions.length!==1||result.newFacts!==0)throw Error('Failure-containment replay did not meet expectations: '+output);
console.log(JSON.stringify({output,...result},null,2));
