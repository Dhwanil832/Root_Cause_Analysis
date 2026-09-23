import { z } from 'zod';
import type { AnalysisSnapshot } from '@/src/domain/types';

export const scenarioSchema = z.object({
  title: z.string().min(3),
  hiddenTruth: z.string().min(20),
  sources: z.array(z.object({
    id: z.string().min(1),
    title: z.string().min(1),
    sourceClass: z.string().min(1),
    text: z.string().min(1),
    available: z.boolean(),
  })).min(1),
}).superRefine((s,ctx) => {
  if(new Set(s.sources.map(x=>x.id)).size !== s.sources.length) ctx.addIssue({code:'custom',message:'Source IDs must be unique.'});
});
export type StoryScenario = z.infer<typeof scenarioSchema>;
// Require meaningful answers/quotes without imposing a character ceiling.
const responseText = (required=false) => z.string().refine(
  text => !required || text.trim().length > 0,
  'Text must be nonempty.',
);
export const storyOutputSchema = z.object({answers:z.array(z.object({
  questionId:z.string(),
  status:z.enum(['answered','partial','unknown','unavailable']),
  answer:responseText(true),
  citations:z.array(z.object({sourceId:z.string(),quote:responseText(true)})),
  limitation:responseText(),
}))});
export type StoryOutput = z.infer<typeof storyOutputSchema>;

// The model chooses evidence. The harness copies the original words without
// asking a model to reproduce punctuation or invent a quotation.
export interface StoryPassage { id: string; sourceId: string; quote: string }
export function storyPassages(scenario: StoryScenario): StoryPassage[] {
  return scenario.sources.filter(source => source.available).flatMap(source => {
    const sentences = source.text.match(/[^.!?]+(?:[.!?]+(?=\s|$)|$)/g) || [source.text];
    const pieces: string[] = [];
    for (const sentence of sentences) {
      let remaining = sentence.trim();
      while (remaining.length > 1400) {
        const space = remaining.lastIndexOf(' ', 1400);
        const end = space > 0 ? space : 1400;
        pieces.push(remaining.slice(0, end));
        remaining = remaining.slice(end).trim();
      }
      if (remaining) pieces.push(remaining);
    }
    return pieces.map((quote, index) => ({ id: `${source.id}:p${index + 1}`, sourceId: source.id, quote }));
  });
}

export const storySelectionSchema = z.object({ answers: z.array(z.object({
  questionId: z.string(), status: z.enum(['answered', 'partial', 'unknown', 'unavailable']),
  answer: responseText(true), passageIds: z.array(z.string()), limitation: responseText(),
})) });

export function resolveStorySelection(selection: z.infer<typeof storySelectionSchema>, questions: { id: string }[], scenario: StoryScenario) {
  const passages = new Map(storyPassages(scenario).map(passage => [passage.id, passage]));
  const output: StoryOutput = { answers: selection.answers.map(answer => ({
    questionId: answer.questionId, status: answer.status, answer: answer.answer, limitation: answer.limitation,
    citations: [...new Set(answer.passageIds)].map(id => {
      const passage = passages.get(id);
      if (!passage) throw new Error(`Unknown or unavailable passage ID: ${id}. Select only IDs from passageCatalog.`);
      return { sourceId: passage.sourceId, quote: passage.quote };
    }),
  })) };
  return validateStoryOutput(storyOutputSchema.parse(output), questions, scenario);
}

export function pendingStoryQuestions(analysis: AnalysisSnapshot) {
  const fetched = new Map(analysis.answerFetches.map(a=>[a.questionId,a.status]));
  const seen = new Set<string>();
  const supplied = new Set(analysis.answers.map(a=>a.questionId));
  return [...analysis.baselineQuestions,...analysis.questions].filter(q=>{
    if(seen.has(q.id)) return false;
    seen.add(q.id);
    return !supplied.has(q.id) && fetched.get(q.id)!=='answered' && !['answered','screened','superseded'].includes(q.status);
  }).map(q=>({id:q.id,text:q.text}));
}

/** Validate membership, full batch coverage and exact source quotations before release. */
export function validateStoryOutput(output:StoryOutput, questions:{id:string}[], scenario:StoryScenario) {
  const expected = new Set(questions.map(q=>q.id));
  const seen = new Set<string>();
  for(const a of output.answers) {
    if(!expected.has(a.questionId) || seen.has(a.questionId)) throw new Error('Story response has unknown or duplicate question IDs.');
    seen.add(a.questionId);
    if(['answered','partial'].includes(a.status) && !a.citations.length) throw new Error('Supported story answers require a source quote.');
    for(const c of a.citations) {
      const source = scenario.sources.find(s=>s.id===c.sourceId && s.available);
      if(!source || !source.text.includes(c.quote)) throw new Error(`Unsupported story citation: ${c.sourceId}; rejected quote: ${JSON.stringify(c.quote.slice(0,500))}. Copy one exact contiguous passage from this source. Do not add ellipses or combine passages from different sources.`);
    }
  }
  if(seen.size!==expected.size) throw new Error('Story response omitted questions. No partial batch was released.');
  return output;
}

export function releasedAnswerText(answer:StoryOutput['answers'][number], scenario:StoryScenario) {
  return [`SIMULATED BENCHMARK ANSWER — ${answer.status}`,answer.answer,
    ...answer.citations.map(c=>{
      const s=scenario.sources.find(s=>s.id===c.sourceId)!;
      return `Support: ${s.id} (${s.sourceClass}; ${s.title})\nExcerpt: ${c.quote}`;
    }),`Limit: ${answer.limitation || 'Synthetic scenario evidence; not an authentic incident record.'}`].join('\n\n');
}
