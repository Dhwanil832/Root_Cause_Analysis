import systemPrompt from '../../prompts/story-agent/system.md?raw';
import { runProviderStage } from '@/src/providers';
import { storySelectionSchema, storyPassages, resolveStorySelection, type StoryScenario, type StoryOutput } from './contracts';
import type { ModelDescriptor } from '@/src/domain/types';
import { overlap } from '@/src/engine/identity';
import { contextCapacity, inputByteCapacity, plannedBytes, TaskContextError } from '@/src/engine/context/planner';
import { reviewInference } from '@/src/engine/review/inference-profile';

/** Private scenario and archive stay in storage. Only a bounded original-source
 * neighborhood and relevant released memory enter an individual question call. */
export function storyPacket(model: ModelDescriptor, scenario: StoryScenario, question: {id:string;text:string}, history: StoryOutput[]) {
  const catalog = storyPassages(scenario).map(p => ({...p, sourceClass: scenario.sources.find(s => s.id === p.sourceId)!.sourceClass,
    title: scenario.sources.find(s => s.id === p.sourceId)!.title}));
  const ranked = catalog.map(p => ({p, score: overlap(question.text, p.title+' '+p.heading+' '+p.tableHeader+' '+p.quote)}))
    .sort((a,b) => b.score-a.score || a.p.id.localeCompare(b.p.id));
  const packet = { questions: [question], passageCatalog: [] as typeof catalog,
    relevantReleasedMemory: [] as StoryOutput['answers'],
    coverage: 'This is a retrieved working set, not the entire private archive. Missing evidence means unknown, not absence. Only passageCatalog is releasable support.' };
  const limit = inputByteCapacity(model);
  if (plannedBytes(systemPrompt,packet,storySelectionSchema)>limit) throw new TaskContextError('The story question itself exceeds the model context.');
  // Reuse relevant prior releases first, then original passages in relevance
  // order. No 3,200-token reserve or 80/20 quota; only native context capacity.
  for (const answer of history.flatMap(h => h.answers).filter(a => overlap(question.text,a.answer)>0)) {
    packet.relevantReleasedMemory.push(answer);
    if (plannedBytes(systemPrompt,packet,storySelectionSchema)>limit) packet.relevantReleasedMemory.pop();
  }
  for (const {p} of ranked) {
    packet.passageCatalog.push(p);
    if (plannedBytes(systemPrompt,packet,storySelectionSchema)>limit) packet.passageCatalog.pop();
  }
  return packet;
}

export async function answerStoryBatch(model:ModelDescriptor, scenario:StoryScenario,
  questions:{id:string;text:string}[], releaseHistory:StoryOutput[], _existingAnswers:unknown[], signal?:AbortSignal) {
  void _existingAnswers;
  const started=Date.now(), answers:StoryOutput['answers']=[], attempts:unknown[]=[];
  for (const question of questions) {
    const packet=storyPacket(model,scenario,question,releaseHistory);
    const result=await runProviderStage({stage:'story-answering',model,systemPrompt,schema:storySelectionSchema,
      schemaName:'story_answer_selection',evidencePacket:packet,contextWindow:contextCapacity(model),noTruncation:true,maxAttempts:1,signal,
      ...reviewInference(model, 'story-answering')});
    const allowed = new Set(packet.passageCatalog.map(p => p.id));
    if (result.output.answers.some(a => a.passageIds.some(id => !allowed.has(id)))) throw new Error('Story selected a passage outside its actual working set.');
    answers.push(...resolveStorySelection(result.output,[question],scenario).answers);
    attempts.push({questionId:question.id,durationMs:result.durationMs,usage:result.usage,
      passageIds:[...allowed],contextBytes:plannedBytes(systemPrompt,packet,storySelectionSchema),
      inference:reviewInference(model, 'story-answering'),providerAttempts:result.attempts});
  }
  return {output:{answers},attempts,engine:model.id,durationMs:Date.now()-started,validation:'valid' as const};
}

export class StoryValidationError extends Error {
  attempts:unknown[];
  constructor(message:string,attempts:unknown[]){super(message);this.attempts=attempts;}
}
