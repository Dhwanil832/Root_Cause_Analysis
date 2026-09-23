import { brokerSchema } from '@/src/domain/schemas';
import { normalizeIntent, stableId } from '@/src/domain/ids';
import type { InvestigationQuestion, ModelDescriptor, SkippedQuestion } from '@/src/domain/types';
import { runAgentStage } from '../run-agent-stage';

export function deterministicBroker(candidates: InvestigationQuestion[]) {
  const kept: InvestigationQuestion[] = [];
  const skipped: SkippedQuestion[] = [];
  const owners = new Map<string, InvestigationQuestion>();
  for (const candidate of candidates) {
    const key = normalizeIntent(candidate.intent) || normalizeIntent(candidate.text);
    const owner = owners.get(key);
    if (!owner) {
      const keptQuestion = { ...candidate, status: candidate.status === 'answered' ? 'answered' as const : 'open' as const };
      owners.set(key, keptQuestion);
      kept.push(keptQuestion);
      continue;
    }
    skipped.push({
      id: stableId('covered', `${candidate.id}:${owner.id}`),
      proposedBy: candidate.tagId,
      text: candidate.text,
      intent: candidate.intent,
      coveredByQuestionId: owner.id,
      coveredByTagId: owner.tagId,
      reason: 'The canonical question already covers the same investigation intent and evidence boundary.',
    });
  }
  return { questions: kept, skipped };
}

export async function runQuestionBroker(model: ModelDescriptor, packet: unknown, candidates: InvestigationQuestion[]) {
  const result = await runAgentStage({
    stage: 'question-broker', model, schema: brokerSchema, schemaName: 'question_broker',
    packet: { packet, candidates: candidates.map((question) => ({ candidateKey: question.id, ...question })) },
  });
  const byId = new Map(candidates.map((question) => [question.id, question]));
  const questions: InvestigationQuestion[] = result.output.canonical.map((item) => {
    const source = byId.get(item.candidateKey);
    const intent = normalizeIntent(item.intent);
    return {
      id: source?.id || stableId('q', `${item.candidateKey}:${intent}`),
      tagId: source?.tagId || 'baseline', proposedBy: source?.proposedBy,
      routedTo: [...new Set([...(source?.routedTo || []), ...item.routedTo])],
      text: item.text, intent, rationale: item.rationale, evidenceNeeded: item.evidenceNeeded,
      priority: item.priority, status: source?.status === 'answered' ? 'answered' : 'open',
    };
  });
  const skipped: SkippedQuestion[] = result.output.covered.flatMap((item) => {
    const source = byId.get(item.candidateKey);
    const owner = questions.find((question) => question.id === item.coveredByCandidateKey)
      || byId.get(item.coveredByCandidateKey);
    if (!source || !owner) return [];
    return [{
      id: stableId('covered', `${source.id}:${owner.id}`), proposedBy: source.tagId,
      text: source.text, intent: source.intent, coveredByQuestionId: owner.id,
      coveredByTagId: owner.tagId, reason: item.reason,
    }];
  });
  return { ...result, questions, skipped };
}
