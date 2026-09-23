import systemPrompt from '../../prompts/story-agent/system.md?raw';
import { runProviderStage } from '@/src/providers';
import { storySelectionSchema, storyPassages, resolveStorySelection, validateStoryOutput, type StoryScenario, type StoryOutput } from './contracts';
import type { ModelDescriptor } from '@/src/domain/types';

export async function answerStoryBatch(model:ModelDescriptor, scenario:StoryScenario,
  questions:{id:string;text:string}[], releaseHistory:StoryOutput[], existingAnswers:unknown[]) {
  const started = Date.now();
  const packet={scenario,releaseHistory,existingAnswers,passageCatalog:storyPassages(scenario)};
  if(JSON.stringify(packet).length>100000) throw new Error('Scenario and memory exceed this run’s context allowance. Nothing was silently truncated.');
  const attempts:unknown[]=[];
  const answers: StoryOutput['answers'] = [];
  // Transport-sized calls, not a cap on investigation questions. Every pending
  // question is processed, sequentially, with the same frozen world and model.
  for (const question of questions) {
    let correction='';
    for(let attempt=0;attempt<2;attempt++) {
      try {
        const evidencePacket={...packet,questions:[question],currentBatchAnswers:answers,correction};
        if(JSON.stringify(evidencePacket).length>100000)throw new Error('Scenario and accumulated answer memory exceed the context allowance. Nothing was truncated.');
        const result=await runProviderStage({stage:'story-answering',model,systemPrompt,
          schema:storySelectionSchema,schemaName:'story_answer_selection',
          evidencePacket});
        attempts.push({questionId:question.id,...result});
        const resolved = resolveStorySelection(result.output,[question],scenario);
        answers.push(...resolved.answers);
        break;
      } catch(error) {
        correction=`Response rejected: ${error instanceof Error?error.message:String(error)}. Answer only this question. Select exact passage IDs from passageCatalog. Unknown/unavailable is appropriate when releasable evidence is missing; do not invent support.`;
        attempts.push({questionId:question.id,error:correction,providerAttempts:(error as {attempts?:unknown})?.attempts});
        if(attempt===1)throw new StoryValidationError(correction,attempts);
      }
    }
  }
  return {output:validateStoryOutput({answers},questions,scenario),attempts,
    engine:model.id,durationMs:Date.now()-started,validation:'valid' as const};
}

export class StoryValidationError extends Error {
  constructor(message:string,public attempts:unknown[]){super(message);}
}
