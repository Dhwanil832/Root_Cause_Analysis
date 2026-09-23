import { brokerSchema } from '@/src/domain/schemas';
import { normalizeIntent, stableId } from '@/src/domain/ids';
import type { InvestigationQuestion, ModelDescriptor, SkippedQuestion } from '@/src/domain/types';
import { runAgentStage } from '../run-agent-stage';

const QUESTION_OPENING = /^(what|which|who|when|where|why|how|did|does|do|is|are|was|were|can|could|would|should|has|have|had)\b/i;

function rejectedQuestion(candidate: InvestigationQuestion, reason: string): SkippedQuestion {
  return {
    id: stableId('rejected-question', `${candidate.id}:${reason}`),
    proposedBy: candidate.tagId,
    text: candidate.text,
    intent: candidate.intent,
    coveredByQuestionId: candidate.id,
    coveredByTagId: candidate.tagId,
    reason,
  };
}

export function questionQualityGate(candidates: InvestigationQuestion[]) {
  const admitted: InvestigationQuestion[] = [];
  const rejected: SkippedQuestion[] = [];
  for (const candidate of candidates) {
    const text = candidate.text.trim();
    if (!text.endsWith('?') || !QUESTION_OPENING.test(text)) {
      rejected.push(rejectedQuestion(candidate, 'Rejected by the quality gate because this is not a clear grammatical question.'));
      continue;
    }
    if (!candidate.intent.trim() || candidate.rationale.trim().length < 16 || !candidate.evidenceNeeded.length) {
      rejected.push(rejectedQuestion(candidate, 'Rejected because it does not identify a distinct intent, rationale, and answerable evidence boundary.'));
      continue;
    }
    admitted.push({
      ...candidate,
      causalBranch: candidate.causalBranch || candidate.intent,
      decisionUnlocked: candidate.decisionUnlocked || candidate.rationale,
    });
  }
  return { admitted, rejected };
}

export function deterministicBroker(candidates: InvestigationQuestion[]) {
  const kept: InvestigationQuestion[] = [];
  const quality = questionQualityGate(candidates);
  const skipped: SkippedQuestion[] = [...quality.rejected];
  const owners = new Map<string, InvestigationQuestion>();
  for (const candidate of quality.admitted) {
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
  const quality = questionQualityGate(candidates);
  if (!quality.admitted.length) throw new Error('No proposed question passed the deterministic quality gate.');
  const result = await runAgentStage({
    stage: 'question-broker', model, schema: brokerSchema, schemaName: 'question_broker',
    packet: { packet, candidates: quality.admitted.map((question) => ({ candidateKey: question.id, ...question })) },
  });
  const byId = new Map(quality.admitted.map((question) => [question.id, question]));
  const questions: InvestigationQuestion[] = result.output.canonical.map((item) => {
    const source = byId.get(item.candidateKey);
    const intent = normalizeIntent(item.intent);
    return {
      id: source?.id || stableId('q', `${item.candidateKey}:${intent}`),
      tagId: source?.tagId || 'baseline', proposedBy: source?.proposedBy,
      routedTo: [...new Set([...(source?.routedTo || []), ...item.routedTo])],
      text: item.text, intent, rationale: item.rationale, evidenceNeeded: item.evidenceNeeded,
      causalBranch: item.causalBranch, decisionUnlocked: item.decisionUnlocked,
      priority: item.priority, status: source?.status === 'answered' ? 'answered' : 'open',
    };
  });
  const skipped: SkippedQuestion[] = [...quality.rejected, ...result.output.covered.flatMap((item) => {
    const source = byId.get(item.candidateKey);
    const owner = questions.find((question) => question.id === item.coveredByCandidateKey)
      || byId.get(item.coveredByCandidateKey);
    if (!source || !owner) return [];
    return [{
      id: stableId('covered', `${source.id}:${owner.id}`), proposedBy: source.tagId,
      text: source.text, intent: source.intent, coveredByQuestionId: owner.id,
      coveredByTagId: owner.tagId, reason: item.reason,
    }];
  })];
  return { ...result, questions, skipped };
}
