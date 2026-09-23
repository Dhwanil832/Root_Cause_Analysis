import test from 'node:test';
import assert from 'node:assert/strict';
import {validateStoryOutput,pendingStoryQuestions,releasedAnswerText,scenarioSchema,storyOutputSchema,restrictStorySources,storyPassages,selectStoryRelease} from '../src/story-agent/contracts.ts';
import {z} from 'zod';
const scenario={title:'Test world',hiddenTruth:'PRIVATE TRUTH MUST NOT APPEAR IN RELEASE',sources:[{id:'s1',title:'Record',sourceClass:'Synthetic',text:'The beam remained stationary.',available:true}]};
const answer={questionId:'q1',status:'answered',answer:'The beam remained stationary.',citations:[{sourceId:'s1',quote:'The beam remained stationary.'}],limitation:''};
test('exact quote and full coverage pass',()=>assert.equal(validateStoryOutput({answers:[answer]},[{id:'q1'}],scenario).answers.length,1));
test('missing and duplicate answers fail',()=>{assert.throws(()=>validateStoryOutput({answers:[]},[{id:'q1'}],scenario));assert.throws(()=>validateStoryOutput({answers:[answer,answer]},[{id:'q1'}],scenario));});
test('unavailable and invented citations fail',()=>{assert.throws(()=>validateStoryOutput({answers:[answer]},[{id:'q1'}],{...scenario,sources:[{...scenario.sources[0],available:false}]}));assert.throws(()=>validateStoryOutput({answers:[{...answer,citations:[{sourceId:'s1',quote:'Invented'}]}]},[{id:'q1'}],scenario));});
test('unknown permitted without fabricated support',()=>assert.doesNotThrow(()=>validateStoryOutput({answers:[{...answer,status:'unknown',citations:[]}]},[{id:'q1'}],scenario)));
test('release does not append hidden scenario',()=>assert.equal(releasedAnswerText(answer,scenario).includes(scenario.hiddenTruth),false));
test('pending questions deduplicate and exclude answered',()=>{const q=id=>({id,text:id,status:'open'});assert.deepEqual(pendingStoryQuestions({baselineQuestions:[q('a')],questions:[q('a'),q('b'),q('c')],answers:[{questionId:'b'}],answerFetches:[{questionId:'c',status:'answered'}]}),[{id:'a',text:'a'}]);});
test('scenario rejects duplicate sources',()=>assert.equal(scenarioSchema.safeParse({...scenario,sources:[scenario.sources[0],scenario.sources[0]]}).success,false));
test('nonempty text is enforced without an arbitrary length cap',()=>{
  assert.equal(storyOutputSchema.safeParse({answers:[{...answer,answer:'x'.repeat(2501)}]}).success,true);
  assert.equal(storyOutputSchema.safeParse({answers:[{...answer,answer:' '}]}).success,false);
  assert.equal(JSON.stringify(z.toJSONSchema(storyOutputSchema,{target:'draft-7'})).includes('maxLength'),false);
});
test('per-round source allowlist excludes later evidence without modifying the archive',()=>{
  const original={...scenario,sources:[...scenario.sources,{id:'later',title:'Later',sourceClass:'Record',available:true,text:'Withheld detail.'}]};
  const restricted=restrictStorySources(original,['s1']);
  assert.deepEqual(storyPassages(restricted).map(p=>p.sourceId),['s1']);
  assert.equal(original.sources[1].available,true);
  assert.throws(()=>restrictStorySources(original,['invented']));
  assert.throws(()=>restrictStorySources(original,[]));
});
test('case-content release preserves answer and quotes without adding benchmark boilerplate',()=>{
  const text=releasedAnswerText({...answer,limitation:'Internal condition remains unverified.'},{...scenario,releaseFormat:'case-content'});
  assert.ok(text.includes(answer.answer));assert.ok(text.includes(answer.citations[0].quote));
  assert.ok(text.includes('Internal condition remains unverified.'));
  assert.ok(!text.includes('SIMULATED'));assert.ok(!text.includes(scenario.hiddenTruth));
  assert.ok(releasedAnswerText(answer,scenario).includes('SIMULATED'));
});
test('reviewed release subset preserves raw rejected answers without releasing them',()=>{
  const candidate={answers:[answer,{...answer,questionId:'q2',answer:'Incorrect candidate'}]};
  const release=selectStoryRelease(candidate,['q1']);
  assert.deepEqual(release.answers,[answer]);assert.equal(candidate.answers.length,2);
  assert.throws(()=>selectStoryRelease(candidate,[]));assert.throws(()=>selectStoryRelease(candidate,['unknown']));
});
