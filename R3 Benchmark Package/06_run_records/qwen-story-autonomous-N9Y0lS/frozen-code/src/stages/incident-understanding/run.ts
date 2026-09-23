import { understandingSchema } from '@/src/domain/schemas';
import { normalizeIntent, stableId } from '@/src/domain/ids';
import type { InvestigationAnswer, InvestigationQuestion, ModelDescriptor } from '@/src/domain/types';
import { runAgentStage } from '../run-agent-stage';

export async function runIncidentUnderstanding(model: ModelDescriptor, packet: unknown, answers: InvestigationAnswer[]) {
  const result = await runAgentStage({ stage: 'incident-understanding', model, schema: understandingSchema, schemaName: 'incident_understanding', packet });
  const questions: InvestigationQuestion[] = result.output.questions.map((candidate) => {
    const intent = normalizeIntent(candidate.intent);
    const id = stableId('bq', intent || candidate.text);
    const answered = answers.some((answer) => answer.questionId === id && answer.text.trim());
    return {
      id, tagId: 'baseline', proposedBy: 'incident-understanding', routedTo: candidate.routedTo,
      text: candidate.text, intent, rationale: candidate.rationale,
      evidenceNeeded: candidate.evidenceNeeded, priority: candidate.priority,
      status: answered ? 'answered' : 'open',
    };
  });
  return { ...result, questions };
}
