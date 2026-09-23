import test from 'node:test';
import assert from 'node:assert/strict';
import {validateStoryOutput,pendingStoryQuestions,releasedAnswerText,scenarioSchema,storyOutputSchema} from '../src/story-agent/contracts.ts';
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
test('runtime text bounds remain enforced without huge grammar repetitions',()=>{
  assert.equal(storyOutputSchema.safeParse({answers:[{...answer,answer:'x'.repeat(2501)}]}).success,false);
  assert.equal(JSON.stringify(z.toJSONSchema(storyOutputSchema,{target:'draft-7'})).includes('maxLength'),false);
});
