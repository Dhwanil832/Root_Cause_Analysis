import test from 'node:test';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {compactCausalPacket,expandCausalPacket} from '../src/knowledge/causal-packet.ts';
import {assertPacketFits} from '../src/knowledge/packet-limits.ts';
import {reconstructCausalInput} from '../../IA-16036 Controlled Evidence Package/06_run_records/tools/reconstruct_causal_input.mjs';

const claim={id:'c',text:'A qualified observation.',kind:'record',status:'unknown',sourceIds:['s']};
const finding={id:'c',statement:claim.text,type:'finding',status:claim.status,sourceIds:claim.sourceIds};
const packet={evidenceClaims:[claim],specialistKnowledgeBases:[{tagId:'equipment-tool',findings:[finding]}],evidenceSegments:[{excerpt:'Original source text.'}]};
test('claim references round-trip exactly and never mutate stored knowledge or sources',()=>{
  const before=structuredClone(packet),compact=compactCausalPacket(packet);
  assert.deepEqual(packet,before);
  assert.deepEqual(compact.specialistKnowledgeBases[0].findings,[{claimRef:'c'}]);
  assert.deepEqual(expandCausalPacket(compact),packet);
});
test('different qualifications, status or sources are retained, not compressed',()=>{
  for(const replacement of [{...finding,testNeeded:'Verify observation.'},{...finding,status:'supported'},{...finding,sourceIds:['other']}]){
    const distinct={...packet,specialistKnowledgeBases:[{findings:[replacement]}]};
    assert.deepEqual(compactCausalPacket(distinct),distinct);
  }
});
test('ambiguous and dangling references fail safely',()=>{
  const duplicate={...packet,evidenceClaims:[claim,{...claim,text:'Different claim'}]};
  assert.deepEqual(compactCausalPacket(duplicate),duplicate);
  assert.throws(()=>expandCausalPacket({...packet,specialistKnowledgeBases:[{findings:[{claimRef:'missing'}]}]}),/Invalid causal claim reference/);
});
test('question field references preserve exact duplicates and distinct decisions',()=>{
  const input={...packet,questions:[{intent:'intent text',causalBranch:'intent text',rationale:'reason',decisionUnlocked:'reason'},
    {intent:'intent text',causalBranch:'another branch',rationale:'reason',decisionUnlocked:'another decision'}]};
  const compact=compactCausalPacket(input);
  assert.deepEqual(compact.questions[0].causalBranch,{sameAs:'intent'});
  assert.deepEqual(compact.questions[1],input.questions[1]);
  assert.deepEqual(expandCausalPacket(compact),input);
});
test('actual stopped B0 input is losslessly reduced below the guard without a new inference',()=>{
  const dir=fileURLToPath(new URL('../../IA-16036 Controlled Evidence Package/06_run_records/qwen-b0-LzLLom/',import.meta.url));
  const original=reconstructCausalInput(dir);
  assert.equal(JSON.stringify(original).length,66798);
  assert.throws(()=>assertPacketFits('causal-analysis',original),/No evidence was truncated/);
  const compact=compactCausalPacket(original);
  assert.deepEqual(expandCausalPacket(compact),original);
  assert.deepEqual(compact.evidenceSegments,original.evidenceSegments);
  assert.deepEqual(compact.evidenceClaims,original.evidenceClaims);
  assert.doesNotThrow(()=>assertPacketFits('causal-analysis',compact));
  console.log(`Saved B0 packet: ${JSON.stringify(original).length} -> ${JSON.stringify(compact).length} characters; exact round-trip passed.`);
});
