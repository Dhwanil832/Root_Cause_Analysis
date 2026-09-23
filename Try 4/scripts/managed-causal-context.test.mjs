import test from 'node:test';
import assert from 'node:assert/strict';
import {previousBoardContext} from '../src/stages/causal-analysis/label-contract.ts';
import {partitionContext,expandContextRecord,runManagedOperation} from '../src/stages/causal-analysis/managed-operation.ts';
import {buildCausalContext} from '../src/stages/causal-analysis/context-plan.ts';
import {contextBudget} from '../src/providers/context-budget.ts';
import {z} from 'zod';

test('working board excludes history without changing archived evidence',()=>{
  const board={focalNodeId:'f',nodes:[{id:'f',label:'Event: A pressure drop was reported',type:'focal-event',status:'unknown',detail:'A qualified detail',sourceIds:['s']}],edges:[],verificationFindings:[{id:'v',targetId:'f',issue:'x'.repeat(160000)}],rejectedEdges:[{id:'r',proposal:{rationale:'old'}}]};
  const before=JSON.stringify(board), working=previousBoardContext(board);
  assert.equal(JSON.stringify(board),before);
  assert.ok(JSON.stringify(working).length<1000);
  assert.equal(working.verificationFindings,undefined);
  assert.equal(working.nodes[0].status,'unknown');
  const context=buildCausalContext({previousBoard:board});
  assert.equal(context.archive.get('f').value.unresolvedIssues[0].issue.length,160000);
});
test('partitioning preserves every complete record in order',()=>{
  const records=Array.from({length:25},(_,i)=>({id:i,text:'qualified fact '+i}));
  const pages=partitionContext(records,page=>page.length<=4);
  assert.deepEqual(pages.flat(),records);
  assert.equal(pages.length,7);
  assert.throws(()=>partitionContext(records,()=>false),/task itself/);
});
test('document retrieval includes every passage, including decimals and final qualifiers',()=>{
  const parts=[{sourceId:'s#1',excerpt:'6.9 | 2.1'}, {sourceId:'s#2',excerpt:'Not a continuous recording.'}];
  assert.deepEqual(expandContextRecord({id:'s',kind:'source-document',value:parts}).map(r=>r.value),parts);
});
test('complete request budget includes prompt and schema rather than packet alone',()=>{
  assert.equal(contextBudget('short',{}, {},'causal-analysis').fits,true);
  assert.equal(contextBudget('x'.repeat(60000),{}, {},'causal-analysis').fits,false);
  assert.equal(contextBudget('',{}, {description:'x'.repeat(60000)},'causal-analysis').fits,false);
});
test('a growing revision catalog is fully paginated rather than copied into every request',async()=>{
  const originalFetch=globalThis.fetch, seen=[];
  const decision={summary:'reviewed',evidenceUsed:[],unknowns:[],alternatives:[],confidence:0.2};
  const schema=z.object({decision:z.object({summary:z.string(),evidenceUsed:z.array(z.string()),unknowns:z.array(z.string()),alternatives:z.array(z.string()),confidence:z.number()}),evidenceRequests:z.array(z.string())});
  globalThis.fetch=async(_url,options)=>{
    const body=JSON.parse(options.body);
    const text=body.messages[1].content;
    const packet=JSON.parse(text.split('--- BEGIN EVIDENCE PACKET ---')[1].split('--- END EVIDENCE PACKET ---')[0]);
    seen.push(...packet.currentTargets.map(t=>t.id));
    return new Response(JSON.stringify({message:{content:JSON.stringify({decision,evidenceRequests:[]})},prompt_eval_count:200,eval_count:20}));
  };
  const targets=Array.from({length:60},(_,i)=>({id:`n${i}`,label:'qualified proposition '.repeat(60)}));
  try {
    const operation=await runManagedOperation({model:{id:'ollama:test',name:'test',provider:'ollama'},schema,schemaName:'revision_test',instruction:'Account for prior targets',packet:{currentTargets:targets},records:[{id:'s',kind:'source-passage',value:{excerpt:'source '.repeat(300)}}]});
    assert.ok(operation.results.length>1);
    assert.deepEqual(seen,targets.map(t=>t.id));
  } finally {globalThis.fetch=originalFetch;}
});
test('model-requested evidence is retrieved once; server context refusal splits only that page',async()=>{
  const originalFetch=globalThis.fetch, requests=[];
  const decision={summary:'checked',evidenceUsed:[],unknowns:[],alternatives:[],confidence:0.3};
  const schema=z.object({decision:z.object({summary:z.string(),evidenceUsed:z.array(z.string()),unknowns:z.array(z.string()),alternatives:z.array(z.string()),confidence:z.number()}),evidenceRequests:z.array(z.string())});
  globalThis.fetch=async(_url,options)=>{
    const body=JSON.parse(options.body); requests.push(body);
    assert.equal(body.truncate,false); assert.equal(body.shift,false);
    if(requests.length===1) return new Response(JSON.stringify({error:'prompt is longer than the context length'}),{status:400});
    return new Response(JSON.stringify({message:{content:JSON.stringify({decision,evidenceRequests:['s']})},prompt_eval_count:500,eval_count:30}));
  };
  try {
    const operation=await runManagedOperation({model:{id:'ollama:test',name:'test',provider:'ollama'},schema,schemaName:'test',instruction:'Read the record',packet:{},
      records:[{id:'a',kind:'claim',value:'a'},{id:'b',kind:'claim',value:'b'}],archive:new Map([['s',{id:'s',kind:'source-document',value:[{sourceId:'s#1',excerpt:'6.9 | 2.1'}]}]])});
    assert.equal(operation.results.length,3);
    assert.equal(requests.length,4);
    assert.equal(operation.audit.filter(r=>r.repartitionedAfterServerRefusal).length,1);
    assert.equal(operation.audit.filter(r=>r.records?.includes('s#1')).length,1);
  } finally {globalThis.fetch=originalFetch;}
});
