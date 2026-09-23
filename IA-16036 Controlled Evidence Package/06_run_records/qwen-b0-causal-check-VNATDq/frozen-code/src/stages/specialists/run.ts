import { specialistSchema } from '@/src/domain/schemas';
import { normalizeIntent, stableId } from '@/src/domain/ids';
import type { InvestigationAnswer, InvestigationQuestion, ModelDescriptor, SpecialistKnowledgeBase, TagResult } from '@/src/domain/types';
import { runAgentStage } from '../run-agent-stage';

export async function runSpecialists(model: ModelDescriptor, packet: unknown, tags: TagResult[], answers: InvestigationAnswer[], previous: SpecialistKnowledgeBase[]) {
  const work = tags.map((tag) => async () => {
    const prior = previous.find((kb) => kb.tagId === tag.id);
    const result = await runAgentStage({
      stage: tag.id, model, schema: specialistSchema, schemaName: `specialist_${tag.id.replaceAll('-', '_')}`,
      specialist: tag.id, packet: { packet, selectedTag: tag, previousKnowledgeBase: prior || null },
    });
    const questions: InvestigationQuestion[] = result.output.questions.map((candidate) => {
      const intent = normalizeIntent(candidate.intent);
      const id = stableId('q', `${tag.id}:${intent || candidate.text}`);
      const answered = answers.some((answer) => answer.questionId === id && answer.text.trim());
      return {
        id, tagId: tag.id, proposedBy: tag.id, routedTo: [...new Set([tag.id, ...candidate.routedTo])],
        text: candidate.text, intent, rationale: candidate.rationale,
        evidenceNeeded: candidate.evidenceNeeded, priority: candidate.priority,
        causalBranch: candidate.causalBranch, decisionUnlocked: candidate.decisionUnlocked,
        status: answered ? 'answered' : 'proposed',
      };
    });
    const knowledgeBase: SpecialistKnowledgeBase = {
      tagId: tag.id, label: tag.label, summary: result.output.summary,
      findings: result.output.findings.map((finding) => ({ ...finding, id: stableId('finding', `${tag.id}:${finding.statement}`) })),
      questionIds: questions.map((question) => question.id), handoffs: result.output.handoffs,
      updatedAt: new Date().toISOString(),
    };
    return { result, questions, knowledgeBase };
  });
  const settled: PromiseSettledResult<Awaited<ReturnType<(typeof work)[number]>>>[] = [];
  const concurrency = model.provider === 'ollama' ? 1 : 3;
  for (let index = 0; index < work.length; index += concurrency) {
    settled.push(...await Promise.allSettled(work.slice(index, index + concurrency).map((run) => run())));
  }

  return {
    successes: settled.flatMap((item) => item.status === 'fulfilled' ? [item.value] : []),
    failures: settled.flatMap((item, index) => item.status === 'rejected' ? [{ tag: tags[index], error: item.reason instanceof Error ? item.reason : new Error('Specialist failed.') }] : []),
  };
}
