import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {cleanCausalLabel,previousBoardContext} from '../src/stages/causal-analysis/label-contract.ts';
import {storyPassages,resolveStorySelection} from '../src/story-agent/contracts.ts';
import {causalCommitProblems} from '../src/orchestrator/commit-contract.ts';

test('prefix removal is narrow, idempotent and preserves uncertainty',()=>{
  for(const prefix of ['Event: ','Focal Event: ','Barrier: ','Condition: ']) {
    assert.equal(cleanCausalLabel(prefix+'Presence remains unknown'),'Presence remains unknown');
  }
  assert.equal(cleanCausalLabel('The barrier was open'),'The barrier was open');
  assert.equal(cleanCausalLabel('Location: R3'),'Location: R3');
  assert.equal(cleanCausalLabel(cleanCausalLabel('Event: Motion occurred')),'Motion occurred');
  assert.throws(()=>cleanCausalLabel('Event:'));
});
test('previous context never mutates committed history or evidence statuses',()=>{
  const board={nodes:[{id:'1',label:'Barrier: Capacity unverified',status:'unknown',sourceIds:['s']}],edges:[]};
  const original=JSON.stringify(board);
  const context=previousBoardContext(board);
  assert.equal(JSON.stringify(board),original);
  assert.equal(context.nodes[0].label,'Capacity unverified');
  assert.equal(context.nodes[0].status,'unknown');
  assert.match(context.authority,/not a source/);
});
test('historical V1-V4 labels replay without semantic changes or file writes',async()=>{
  for(let v=1;v<=4;v++) {
    const file=new URL(`../../R3 Benchmark Package/06_run_records/qwen-followup/version-${v}.json`,import.meta.url);
    const snapshot=JSON.parse(await fs.readFile(file,'utf8'));
    const old=snapshot.analysis.causalBoard;
    const clean=previousBoardContext(old);
    assert.equal(clean.nodes.length,old.nodes.length);
    assert.deepEqual(clean.edges.map(e=>e.id),old.edges.map(e=>e.id));
    for(let i=0;i<old.nodes.length;i++) {
      assert.equal(clean.nodes[i].status,old.nodes[i].status);
      assert.deepEqual(clean.nodes[i].sourceIds,old.nodes[i].sourceIds);
      assert.equal(cleanCausalLabel(clean.nodes[i].label),clean.nodes[i].label);
    }
  }
});
const world={title:'Fixed test world',hiddenTruth:'PRIVATE material never released by the resolver',sources:[
  {id:'s',title:'Review',sourceClass:'Synthetic',available:true,text:'The report was unavailable. Physical absence was not established.'},
  {id:'private',title:'Unavailable',sourceClass:'Synthetic',available:false,text:'This is not releasable.'},
]};
test('passage catalog contains exact source substrings and no unavailable sources',()=>{
  const catalog=storyPassages(world);
  assert.equal(catalog.length,2);
  for(const passage of catalog) assert.ok(world.sources.find(s=>s.id===passage.sourceId).text.includes(passage.quote));
});
test('passage resolver materializes exact source text, not model quotations',()=>{
  const result=resolveStorySelection({answers:[{questionId:'q',status:'partial',answer:'The record is unavailable.',passageIds:['s:p1'],limitation:'Physical presence unknown.'}]},[{id:'q'}],world);
  assert.deepEqual(result.answers[0].citations,[{sourceId:'s',quote:'The report was unavailable.'}]);
  assert.equal(JSON.stringify(result).includes('PRIVATE'),false);
});
test('invalid citations, unavailable evidence and missing answers still fail closed',()=>{
  const response=ids=>({answers:[{questionId:'q',status:'partial',answer:'A claim.',passageIds:ids,limitation:''}]});
  for(const ids of [['made-up'],['private:p1'],[]]) assert.throws(()=>resolveStorySelection(response(ids),[{id:'q'}],world));
  assert.throws(()=>resolveStorySelection({answers:[]},[{id:'q'}],world));
});
test('strict commit requires executed analysis and verification, not causal certainty',()=>{
  const snapshot={stageErrors:[],trace:[{stage:'causal-analysis',engine:'ollama:qwen3.5:latest',validation:'valid'},{stage:'causal-verification',engine:'ollama:qwen3.5:latest',validation:'valid'}],causalBoard:{focalNodeId:'f',nodes:[{id:'f',status:'unknown'}]}};
  assert.deepEqual(causalCommitProblems(snapshot),[]);
  assert.ok(causalCommitProblems({...snapshot,trace:[]}).length);
  assert.ok(causalCommitProblems({...snapshot,stageErrors:[{stage:'causal-analysis',message:'invalid JSON'}]}).length);
});
