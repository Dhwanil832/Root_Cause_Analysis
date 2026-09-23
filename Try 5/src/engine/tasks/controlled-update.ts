import type { EngineState, TaskKind } from '../types';
import { findingText } from '../records';
import { reconcileAnswers } from '@/src/stages/question-broker/task';

type Schedule = (state: EngineState, kind: TaskKind, owner: string, ids: string[], query: string, required?: string[]) => Promise<void>;

/** A finite operator-defined evidence release, using the unmodified task prompts,
 * model, executor and evidence gates. Not a numeric model/question/token limit.
 * Preserve all old knowledge; do not restart the inherited investigation queue.
 * Newly suggested follow-ups remain visible for a subsequent evidence release. */
export async function planControlledUpdate(state: EngineState, schedule: Schedule) {
  const scope = state.controlledUpdate!;
  const addedDocumentSpans = state.sources.filter(s => state.changedSourceIds.includes(s.id) && s.origin === 'document')
    .flatMap(s => s.spans.map(p => p.id));
  const required = (ids: string[]) => [...new Set([...ids, ...addedDocumentSpans])];
  for (;;) {
    for (const task of state.tasks.filter(t => t.status === 'queued')) {
      if (task.dependsOn.some(id => !state.tasks.some(t => t.id === id) || state.tasks.some(t => t.id === id && ['failed', 'blocked'].includes(t.status)))) {
        task.status = 'blocked'; task.error = 'Required producer/reviewer failed; dependent inference was not run.';
      }
    }
    const next = state.tasks.find(t => t.status === 'queued' && t.dependsOn.every(id => state.tasks.some(d => d.id === id && d.status === 'completed')));
    if (next) return next;
    if (state.tasks.some(t => t.status === 'running')) return null;
    if (state.tasks.some(t => t.status === 'queued')) { state.pauseReason = 'Controlled update has unresolved task dependencies.'; return null; }
    const stage = scope.stage++;
    state.phase = Math.min(10, stage + 5);
    if (stage === 0) {
      for (const id of scope.questionIds) {
        const q = state.questions.find(q => q.id === id)!;
        const answerSpans = state.sources.filter(s => s.questionId === id).flatMap(s => s.spans.map(p => p.id));
        await schedule(state, 'answer', 'answer-fetching', [id], `${q.text} ${q.intent} ${q.subject} ${q.location} ${q.time}`, required([...q.spanIds, ...answerSpans]));
      }
    } else if (stage === 1) {
      const answerFindings = new Set(scope.questionIds.flatMap(id => state.questions.find(q => q.id === id)?.findingIds || []));
      scope.reviewFindingIds = state.findings.filter(f => scope.baselineRevisions[f.id] !== f.revision || answerFindings.has(f.id)).map(f => f.id);
      for (const id of scope.reviewFindingIds) {
        const f = state.findings.find(f => f.id === id)!;
        await schedule(state, 'review', 'claim-review', [id], findingText(f), required(f.spanIds));
      }
    } else if (stage === 2) {
      reconcileAnswers(state);
      for (const id of scope.reviewFindingIds) {
        const f = state.findings.find(f => f.id === id)!;
        if (f.kind !== 'context' && state.tasks.some(t => t.kind === 'review' && t.targetIds.includes(id) && t.status === 'completed'))
          await schedule(state, 'causal', 'causal-analysis', [id], findingText(f), required(f.spanIds));
      }
    } else if (stage === 3) {
      // Review every retained board statement against the release; a rich old
      // board must not silently retain stale approval after contradictory facts.
      for (const p of state.propositions) await schedule(state, 'verify', 'causal-verification', [p.id], `${p.label} ${p.detail}`, required(p.spanIds));
    } else if (stage === 4) {
      const nodes = new Set(['focal', ...state.propositions.map(p => p.id)]);
      for (const e of state.relationships) {
        if (!nodes.has(e.from) || !nodes.has(e.to) || !e.proposedBy?.length) {
          e.status = 'unknown'; e.reviewReason = 'No current proposal or supported board endpoint; not an established causal connection.'; continue;
        }
        await schedule(state, 'verify', 'causal-verification', [e.id], `${e.rationale} ${e.counterfactual} ${e.alternative}`, required(e.spanIds));
      }
    } else {
      scope.stage = 5; state.phase = 10;
      reconcileAnswers(state);
      return null;
    }
  }
}
