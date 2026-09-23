import test from 'node:test';
import assert from 'node:assert/strict';
import {createEvidenceIndex} from '../src/stages/causal-analysis/evidence-index.ts';
import {consolidationProblems,consolidateCandidates} from '../src/stages/causal-analysis/consolidate.ts';
import {coalesceEdges} from '../src/stages/causal-analysis/edge-identity.ts';
import {groundReview} from '../src/stages/causal-verification/review-contract.ts';
import {runFocusedOperation} from '../src/stages/causal-analysis/focused-operation.ts';
import {runCausalVerification} from '../src/stages/causal-verification/run.ts';
import {z} from 'zod';

const decision={summary:'Test',evidenceUsed:[],unknowns:[],alternatives:[],confidence:0.2};
const sources=[{sourceId:'log#1',documentId:'log',label:'shift.md · section 1',excerpt:'Work was paused.'},
  {sourceId:'meter#1',documentId:'meter',label:'readings.md · section 1',excerpt:'The receiving pressure fell in the recorded samples. Not a continuous recording.'}];
const claims=[{id:'claim-a',text:'A measurement claim with an incorrect draft citation',sourceIds:['shift.md']}];

test('claim IDs, document IDs and filenames resolve without inventing missing evidence',()=>{
  const index=createEvidenceIndex({evidenceSegments:sources,evidenceClaims:claims});
  const resolution=index.resolve(['claim-a']);
  assert.deepEqual(resolution.claimIds,['claim-a']);
  assert.deepEqual(resolution.sourceIds,['log#1']); // NOT automatically corrected to meter#1
  assert.deepEqual(index.resolve(['meter']).sourceIds,['meter#1']);
  assert.deepEqual(index.resolve(['kb:unknown']).unresolved,['kb:unknown']);
  assert.deepEqual(index.workingSet(['claim-a'],claims).coverage.omitted,[]);
});
test('cyclic claims and ambiguous filename aliases fail closed',()=>{
  const index=createEvidenceIndex({evidenceSegments:[...sources,{...sources[0],sourceId:'other#1',documentId:'other'}],
    evidenceClaims:[{id:'a',text:'A',sourceIds:['b']},{id:'b',text:'B',sourceIds:['a']}]});
  assert.deepEqual(index.resolve(['a']).unresolved,['a']);
  assert.deepEqual(index.resolve(['shift.md']).unresolved,['shift.md']);
});
test('consolidation preserves meaningful unknowns and prohibits merge cycles or disappearing targets',()=>{
  const row={disposition:'merge',reason:'same proposition',targetKey:'b',proposition:null,question:''};
  const sets=[new Set(['focal']),new Set(['a','b'])];
  assert.ok(consolidationProblems({a:row,b:{...row,targetKey:'a'}},...sets).length);
  assert.ok(consolidationProblems({a:row,b:{...row,disposition:'context',targetKey:null}},...sets).length);
  assert.deepEqual(consolidationProblems({a:{...row,disposition:'question',targetKey:null,question:'What was its actual state?'}},...sets),[]);
});
test('duplicate endpoint/type proposals produce one edge; rejected variants cannot make it supported',()=>{
  const edge={fromKey:'a',toKey:'b',type:'enabled',rationale:'possible',status:'supported',sourceIds:['s'],claimIds:[],counterfactual:'x',competingExplanation:'y',evidenceGap:'z'};
  const result=coalesceEdges([edge,{...edge,rationale:'same relation rewritten'},{...edge,status:'rejected'}]);
  assert.equal(result.active.length,1);assert.equal(result.active[0].status,'unknown');
  assert.equal(result.rejected.length,1);assert.equal(result.variants[0].proposals.length,3);
});
test('unused fields cannot turn a question into a board node or abort consolidation',()=>{
  const row={disposition:'question',reason:'The underlying state is unknown',targetKey:'irrelevant',
    question:'What was the state?',proposition:{type:'condition',label:'Unknown state',detail:'',assessmentKind:'observation',sourceIds:[],claimIds:['not-consumed']}};
  assert.deepEqual(consolidationProblems({q:row},new Set(['focal']),new Set(['q'])),[]);
});
test('unsupported or fabricated review citations downgrade only their own target',()=>{
  const records=sources.map(s=>({id:s.sourceId,kind:'source-passage',value:s}));
  const row={verdict:'supported',issue:'',evidenceNeeded:'',question:'',citations:[{sourceId:'log#1',quote:'Work was paused.'}]};
  assert.equal(groundReview(row,records).verdict,'supported');
  assert.equal(groundReview({...row,citations:[{sourceId:'log#1',quote:'Valve was closed.'}]},records).verdict,'insufficient');
  assert.equal(groundReview({...row,verdict:'viable-hypothesis',citations:[]},records).verdict,'viable-hypothesis');
});
test('a focused operation splits targets while retaining all selected evidence',async()=>{
  const original=globalThis.fetch,seen=[];
  globalThis.fetch=async(_url,options)=>{
    const body=JSON.parse(options.body),packet=JSON.parse(body.messages[1].content.split('--- BEGIN EVIDENCE PACKET ---')[1].split('--- END EVIDENCE PACKET ---')[0]);
    seen.push(packet);return new Response(JSON.stringify({message:{content:JSON.stringify({decision})},prompt_eval_count:200,eval_count:20}));
  };
  const targets=Array.from({length:20},(_,id)=>({id,label:'x'.repeat(3500)}));
  const records=sources.map(s=>({id:s.sourceId,kind:'source-passage',value:s}));
  try {
    await runFocusedOperation({model:{id:'ollama:test',name:'test',provider:'ollama'},schemaName:'split_task',systemPrompt:'Test',targets,records,
      schemaFor:()=>z.object({decision:z.object({summary:z.string(),evidenceUsed:z.array(z.string()),unknowns:z.array(z.string()),alternatives:z.array(z.string()),confidence:z.number()})}),packetFor:owned=>({targets:owned})});
    assert.ok(seen.length>1);assert.deepEqual(seen.flatMap(p=>p.targets),targets);
    assert.ok(seen.every(p=>JSON.stringify(p.retrievedEvidence)===JSON.stringify(records)));
  } finally {globalThis.fetch=original;}
});
test('verification sees underlying and complementary sources jointly; each target is assessed once',async()=>{
  const original=globalThis.fetch,seen=[];
  globalThis.fetch=async(_url,options)=>{
    const body=JSON.parse(options.body),packet=JSON.parse(body.messages[1].content.split('--- BEGIN EVIDENCE PACKET ---')[1].split('--- END EVIDENCE PACKET ---')[0]);seen.push(packet);
    const reviews=Object.fromEntries(packet.targets.map(t=>[t.id,{verdict:t.id==='fact'?'supported':'viable-hypothesis',issue:t.id==='fact'?'':'Mechanism is unresolved.',evidenceNeeded:'',question:'',citations:t.id==='fact'?[{sourceId:'meter#1',quote:'The receiving pressure fell in the recorded samples.'}]:[]}]));
    return new Response(JSON.stringify({message:{content:JSON.stringify({reviews,decision})},prompt_eval_count:200,eval_count:20}));
  };
  const board={focalNodeId:'fact',nodes:[{id:'fact',type:'focal-event',label:'Recorded receiving pressure fell',detail:'',status:'proposed',sourceIds:['claim-a'],specialistIds:[],verified:false},{id:'hyp',type:'condition',label:'A possible restriction remains untested',detail:'',status:'unknown',sourceIds:[],specialistIds:[],assessmentKind:'hypothesis',verified:false}],edges:[],verificationFindings:[]};
  try {
    const result=await runCausalVerification({id:'ollama:test',name:'test',provider:'ollama'},{evidenceSegments:sources,evidenceClaims:claims},board,new Map());
    assert.equal(seen.length,1);assert.deepEqual(new Set(seen[0].retrievedEvidence.map(r=>r.id)),new Set(['log#1','meter#1']));
    assert.equal(result.board.nodes[0].verified,true);assert.equal(result.board.nodes[1].status,'unknown');
    assert.ok(!result.board.verificationFindings.some(f=>f.targetId==='hyp'&&f.severity==='blocking'));
  } finally {globalThis.fetch=original;}
});
test('a malformed merge is quarantined locally while a neighboring question survives',async()=>{
  const original=globalThis.fetch;
  const proposed={type:'condition',label:'Uncertain valve position',detail:'',assessmentKind:'observation',sourceIds:['log#1'],claimIds:[]};
  globalThis.fetch=async()=>new Response(JSON.stringify({message:{content:JSON.stringify({decision,dispositions:{
    a:{disposition:'merge',targetKey:'a',reason:'Malformed self merge',question:'',proposition:null},
    b:{disposition:'question',targetKey:null,reason:'Unknown field state',question:'What was the valve position?',proposition:proposed},
  }})},prompt_eval_count:200,eval_count:20}));
  const node={type:'condition',label:'An unresolved condition',detail:'',status:'unknown',sourceIds:['log#1'],specialistIds:[]};
  try {
    const result=await consolidateCandidates({id:'ollama:test',name:'test',provider:'ollama'},{evidenceSegments:sources},[{...node,key:'a'},{...node,key:'b'}],{...node,label:'An interruption was reported'});
    assert.equal(result.ledger.length,2);assert.equal(result.catalog.length,1);
    assert.equal(result.ledger[0].disposition,'question');assert.match(result.ledger[0].reason,/could not safely account/);
    assert.equal(result.ledger[1].question,'What was the valve position?');
    assert.equal(result.results.length,1); // no whole-batch retry
  } finally {globalThis.fetch=original;}
});
