import { answerFetchSchema } from '@/src/domain/schemas';
import { stableId } from '@/src/domain/ids';
import type { AnswerFetchResult, DocumentRecord, EvidenceClaim, InvestigationAnswer, InvestigationQuestion, ModelDescriptor, SpecialistKnowledgeBase, TraceEntry } from '@/src/domain/types';
import { retrieveForQuestion } from '@/src/knowledge/retrieval';
import { runAgentStage } from '../run-agent-stage';
import { z } from 'zod';

export async function runAnswerFetchers(model: ModelDescriptor, packet: unknown, questions: InvestigationQuestion[], documents: DocumentRecord[], answers: InvestigationAnswer[], knowledgeBases: SpecialistKnowledgeBase[]) {
  const targets = questions.filter((question) => question.status !== 'answered');
  const work = targets.map((question) => async () => {
    const sources = retrieveForQuestion(question, documents, answers, knowledgeBases);
    const answerableSources = sources.filter((source) => source.scope !== 'specialist-kb');
    if (!answerableSources.length) {
      const fetch: AnswerFetchResult = {
        id: stableId('fetch', question.id), questionId: question.id, status: 'not-found', answer: '',
        sourceIds: [], claimIds: [], searched: ['reference documents', 'incident documents', 'track answers', 'specialist knowledge bases'],
        userRequest: `Please provide what is known about: ${question.text}`,
      };
      return { fetch, claims: [] as EvidenceClaim[], trace: null as TraceEntry | null };
    }
    const result = await runAgentStage({
      stage: 'answer-fetching', model, schema: answerFetchSchema.extend({
        claims: z.array(answerFetchSchema.shape.claims.element.extend({ status: z.enum(['proposed', 'unknown']) })).max(12),
      }), schemaName: 'answer_fetch',
      instruction: 'All extracted claims are candidates pending separate evidence review. Use proposed or unknown; never self-certify a claim as supported or verified.',
      packet: {
        question,
        retrievedSources: answerableSources,
        specialistLeads: sources.filter((source) => source.scope === 'specialist-kb'),
        investigationContext: packet,
      },
    });
    const claims: EvidenceClaim[] = result.output.claims.map((claim) => ({
      ...claim, id: stableId('claim', `${question.id}:${claim.text}`), questionId: question.id,
    }));
    const fetch: AnswerFetchResult = {
      id: stableId('fetch', question.id), questionId: question.id, status: result.output.status,
      answer: result.output.answer, sourceIds: result.output.sourceIds,
      claimIds: claims.map((claim) => claim.id), userRequest: result.output.userRequest,
      searched: ['Lexically selected excerpts only; not an exhaustive absence check.', ...answerableSources.map(source => source.label)],
    };
    return { fetch, claims, trace: result.trace };
  });
  const settled: PromiseSettledResult<Awaited<ReturnType<(typeof work)[number]>>>[] = [];
  // The number of workers is dynamic; the concurrency cap protects a local model
  // server from receiving every evidence request at once.
  const concurrency = model.provider === 'ollama' ? 1 : 3;
  for (let index = 0; index < work.length; index += concurrency) {
    settled.push(...await Promise.allSettled(work.slice(index, index + concurrency).map((run) => run())));
  }
  return {
    successes: settled.filter((item): item is PromiseFulfilledResult<Awaited<ReturnType<(typeof work)[number]>>> => item.status === 'fulfilled').map((item) => item.value),
    failures: settled.flatMap((item, index) => item.status === 'rejected' ? [{ question: targets[index], error: item.reason instanceof Error ? item.reason : new Error('Answer fetch failed.') }] : []),
  };
}
