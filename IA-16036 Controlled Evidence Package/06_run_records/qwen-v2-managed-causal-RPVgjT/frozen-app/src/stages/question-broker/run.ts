import { decisionSchema } from '@/src/domain/schemas';
import { z } from 'zod';
import { stableId } from '@/src/domain/ids';
import type { InvestigationQuestion, ModelDescriptor, SkippedQuestion } from '@/src/domain/types';
import { runAgentStage } from '../run-agent-stage';
import { brokerBatchProblems, brokerInBatches, type BrokerDisposition } from './batches';
import type { TraceEntry } from '@/src/domain/types';
import { PROMPT_VERSION } from '@/src/prompts/manifest';

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
  const normalize = (text: string) => text.trim().toLowerCase().replace(/\s+/g, ' ');
  for (const candidate of quality.admitted) {
    // This also runs after causal/verification questions arrive. It must not
    // undo the model broker's decision to retain partially overlapping questions.
    const key = JSON.stringify([
      normalize(candidate.intent), normalize(candidate.text),
      normalize(candidate.causalBranch || ''), normalize(candidate.decisionUnlocked || ''),
      candidate.evidenceNeeded.map(normalize).sort(),
      candidate.status === 'answered' ? candidate.id : '',
    ]);
    const owner = owners.get(key);
    if (!owner) {
      const keptQuestion = { ...candidate, status: candidate.status === 'proposed' ? 'open' as const : candidate.status };
      owners.set(key, keptQuestion);
      kept.push(keptQuestion);
      continue;
    }
    owner.routedTo = [...new Set([...(owner.routedTo || []), ...(candidate.routedTo || [])])];
    skipped.push({
      id: stableId('covered', `${candidate.id}:${owner.id}`),
      proposedBy: candidate.tagId,
      text: candidate.text,
      intent: candidate.intent,
      coveredByQuestionId: owner.id,
      coveredByTagId: owner.tagId,
      reason: 'Exact duplicate wording, intent, branch, decision and evidence boundary; all specialist routing retained.',
    });
  }
  return { questions: kept, skipped };
}

export async function runQuestionBroker(model: ModelDescriptor, packet: unknown, candidates: InvestigationQuestion[]) {
  const quality = questionQualityGate(candidates);
  const batches: Array<{ candidateIds: string[]; catalogIds: string[]; output: unknown; trace: TraceEntry; providerAttempts: unknown }> = [];
  let result: Awaited<ReturnType<typeof brokerInBatches>>;
  try {
    result = await brokerInBatches(quality.admitted, async (batch, catalog) => {
      const compact = (q: InvestigationQuestion) => ({
        candidateKey: q.id, text: q.text, intent: q.intent, rationale: q.rationale,
        causalBranch: q.causalBranch, decisionUnlocked: q.decisionUnlocked,
        evidenceNeeded: q.evidenceNeeded, status: q.status, routedTo: q.routedTo,
      });
      const response = await runAgentStage({
        stage: 'question-broker', model,
        schema: z.object({
          assignments: z.object(Object.fromEntries(batch.map((q, index) => [q.id, z.object({
            owner: z.enum((q.status === 'answered' ? [q.id] : [...new Set([q.id, ...catalog.map(q => q.id), ...batch.slice(0, index).map(q => q.id)])]) as [string, ...string[]]),
            reason: z.string().min(1).max(500),
          }).strict()]))).strict(), decision: decisionSchema,
        }), schemaName: 'question_ownership',
        packet: { packet, candidates: batch.map(compact), canonicalQuestions: catalog.map(compact) },
        instruction: 'For each application-owned candidate key, select one owner. Select its own key to KEEP the question, or a permitted earlier question key only when that question fully covers it. Do not emit disposition or coveredByCandidateKey fields. The app derives those. Preserve answered-question ownership.',
      });
      batches.push({ candidateIds: batch.map(q => q.id), catalogIds: catalog.map(q => q.id), ...response });
      const owners = new Map<string, string>();
      const decisions: BrokerDisposition[] = batch.map(q => {
        const assignment = response.output.assignments[q.id];
        const owner = owners.get(assignment.owner) || assignment.owner;
        owners.set(q.id, owner);
        return { candidateKey: q.id, disposition: owner === q.id ? 'keep' : 'covered',
          coveredByCandidateKey: owner === q.id ? '' : owner, reason: assignment.reason };
      });
      const problems = brokerBatchProblems({ decisions }, batch, catalog);
      if (problems.length) throw new Error(problems.join('; '));
      return { decisions };
    });
  } catch (error) {
    throw Object.assign(error instanceof Error ? error : new Error('Broker batch failed.'), { brokerBatches: batches });
  }
  const byId = new Map(quality.admitted.map((question) => [question.id, question]));
  const questions: InvestigationQuestion[] = result.canonical.map(q => ({
    ...q, status: q.status === 'answered' ? 'answered' : 'open', routedTo: [...(q.routedTo || [])],
  }));
  const skipped: SkippedQuestion[] = [...quality.rejected,
    ...result.covered.map((item) => {
    const source = byId.get(item.candidateKey)!;
    const owner = questions.find((question) => question.id === item.coveredByCandidateKey)!;
    owner.routedTo = [...new Set([...(owner.routedTo || []), ...(source.routedTo || [])])];
    if (source.priority === 'high' || (source.priority === 'medium' && owner.priority === 'low')) owner.priority = source.priority;
    return {
      id: stableId('covered', `${source.id}:${owner.id}`), proposedBy: source.tagId,
      text: source.text, intent: source.intent, coveredByQuestionId: owner.id,
      coveredByTagId: owner.tagId, reason: item.reason,
    };
  })];
  const trace: TraceEntry = {
    id: crypto.randomUUID(), stage: 'question-broker', promptVersion: PROMPT_VERSION,
    engine: batches[0]?.trace.engine || 'harness',
    durationMs: batches.reduce((sum, batch) => sum + batch.trace.durationMs, 0),
    validation: batches.some(batch => batch.trace.validation === 'repaired') ? 'repaired' : 'valid',
    summary: `${quality.admitted.length} candidates processed in ${batches.length} bounded calls; ${questions.length} retained, ${result.covered.length} covered. Original question wording and routing preserved.`,
    evidence: [], unknowns: [], alternatives: [],
    confidence: batches.length ? Math.min(...batches.map(batch => batch.trace.confidence)) : 1,
  };
  return { questions, skipped, trace, batches };
}
