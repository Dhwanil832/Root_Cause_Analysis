import { initializeState as initializeLedger } from '../tasks/legacy-planner';
import { digest } from '../identity';
import type { EngineInput, EngineState, EngineTask, TaskKind } from '../types';
import { emptyPosition } from './types';
import { syncBoardEvidence } from './apply';
import { invalidateReview } from '../review/interpretation';
import { activeBoardFindings } from './usability';
import { currentBoardPremiseIds, retireObsoleteQueuedReviews } from './review-dependencies';

export async function initializeState(input: EngineInput, version: number, previous: EngineState | null): Promise<EngineState> {
  const state = await initializeLedger(input, version, previous);
  const position = state.investigation ||= emptyPosition();
  position.ready = false; position.stage = 'Reading new evidence';
  position.priorQuestionIds = state.questions.map(q => q.id);
  position.priorBranchIds = position.branches.map(b => b.id);
  position.changedFindingIds = [];
  const valid = new Set(state.sources.flatMap(s => s.spans.map(p => p.id)));
  position.readSpanIds = position.readSpanIds.filter(id => valid.has(id));
  if (previous && state.changedSourceIds.length) for (const finding of state.findings.filter(f => position.selectedFindingIds.includes(f.id)))
    invalidateReview(finding, 'unreviewed', 'New original evidence requires the selected map premise to be rechecked in this version.', state);
  state.phase = input.humanDecision && !state.changedSourceIds.length ? 8 : 0;
  state.progressiveBoard = false;
  return state;
}

async function add(state: EngineState, kind: TaskKind, owner: string, ids: string[], query: string, required: string[] = []) {
  const id = await digest(['investigation-led-v1', kind, owner, ids, query, required]);
  if (state.tasks.some(t => t.id === id)) return;
  state.tasks.push({ id, kind, owner, targetIds: ids, query, requiredSpanIds: [...new Set(required)], dependsOn: [],
    status: 'queued', attempts: 0, cacheKey: '', error: '', reused: false, evidenceIds: [], omittedEvidenceIds: [],
    contextBytes: 0, durationMs: 0, inputTokens: 0, outputTokens: 0, createdAt: new Date().toISOString() });
}
const steps = ['Read changed evidence', 'Frame the incident and competing explanations', 'Consult specialists on named gaps',
  'Resolve and merge current evidence directions', 'Consolidate the investigative position', 'Check board premises',
  'Verify proposed connections', 'Publish position and concrete evidence requests', 'Human-approved corrective actions'];

/** Deliverable dependencies, not a recursively growing to-do list or a question quota. */
export async function planNext(state: EngineState): Promise<EngineTask | null> {
  if (state.pauseReason) return null;
  const position = state.investigation ||= emptyPosition();
  if (state.pauseAfterTaskId) {
    const selected = state.tasks.find(t => t.id === state.pauseAfterTaskId && t.status === 'queued');
    if (selected) return selected;
    state.pauseReason = 'Selected recovery task is not runnable; no other task started.'; return null;
  }
  while (true) {
    if (state.phase === 6) retireObsoleteQueuedReviews(state);
    const queued = state.tasks.find(t => t.status === 'queued');
    if (queued) return queued;
    const foundation = state.tasks.find(t => ['read','frame'].includes(t.kind) && ['failed','blocked'].includes(t.status));
    if (foundation) { state.pauseReason = `Prerequisite ${foundation.kind} failed: ${foundation.error}`; return null; }
    if (state.phase >= 9) { position.ready = true; position.stage = 'Position published — evidence requests remain open'; return null; }
    if ([2, 5].includes(state.phase) && activeBoardFindings(state).length) {
      const kind = state.phase === 2 ? 'frame' : 'refine';
      const map = state.tasks.find(t => t.kind === kind && t.status === 'completed');
      if (map) {
        await add(state, 'connect', 'causal-analysis', [map.id], 'Propose or revise connections using only the selected board nodes. Request missing endpoints separately.');
        const connection = state.tasks.find(t => t.kind === 'connect' && t.targetIds.includes(map.id) && t.status === 'queued');
        if (connection) { position.stage = 'Connect selected board nodes'; return connection; }
      }
    }
    const phase = state.phase++;
    position.stage = steps[phase];
    if (phase === 0) {
      for (const source of state.sources) {
        for (const span of source.spans.filter(p => !position.readSpanIds.includes(p.id)))
          await add(state, 'read', 'evidence-reading', [span.id], source.label, [span.id]);
        if (!source.spans.length) {
          await add(state, 'read', 'evidence-reading', [source.id], source.label);
          const task = state.tasks.at(-1)!; task.status = 'blocked'; task.error = `No readable original evidence: ${source.label}. Supply extracted text or supported visual evidence.`;
        }
      }
    }
    if (phase === 1) {
      position.changedFindingIds = state.findings.filter(f => f.updatedVersion === state.version
        || f.spanIds.some(id => state.sources.some(s => state.changedSourceIds.includes(s.id) && s.spans.some(p => p.id === id)))).map(f => f.id);
      await add(state, 'frame', 'causal-analysis', [], 'Understand the incident collectively; select map premises and discriminating evidence directions.');
    }
    if (phase === 2) for (const mission of position.consultations.filter(c => !c.completedVersion)) {
      const branch = position.branches.find(b => b.id === mission.branchId);
      await add(state, 'consult', mission.domain, [mission.id], `${branch?.title} ${mission.purpose}`);
    }
    if (phase === 3) {
      // A canonical request belongs to every interested branch, but is searched once.
      const groups = new Map<string, string[]>();
      for (const direction of position.directions) {
        const q = state.questions.find(q => q.id === direction.questionId);
        if (!q || q.coveredBy || (q.status === 'answered' && !state.changedSourceIds.length)) continue;
        if (q.inventory && !state.changedSourceIds.length) continue;
        const key = direction.branchIds[0];
        groups.set(key, [...(groups.get(key) || []), q.id]);
      }
      for (const [branch, ids] of groups) {
        const questions = state.questions.filter(q => ids.includes(q.id));
        const required = state.sources.filter(s => s.questionId && ids.includes(s.questionId)).flatMap(s => s.spans.map(p => p.id));
        await add(state, 'resolve', 'answer-fetching', ids, `${branch} ${questions.map(q => `${q.text} ${q.decision}`).join('\n')}`, required);
      }
    }
    if (phase === 4 && state.tasks.some(t => ['consult','resolve'].includes(t.kind)))
      await add(state, 'refine', 'causal-analysis', [], 'Consolidate consultations and retrieved evidence. Preserve alternatives and expose the next evidence directions.');
    if (phase === 5) for (const id of currentBoardPremiseIds(state)) {
      const f = state.findings.find(f => f.id === id);
      if (!f || !f.spanIds.length) continue;
      // New original evidence can contradict an old premise even if its wording did not change.
      if (f.reviewExecution !== 'complete' || state.changedSourceIds.length)
        await add(state, 'review', 'claim-review', [f.id], f.statement, f.spanIds);
    }
    if (phase === 6) {
      syncBoardEvidence(state);
      for (const edge of state.relationships.filter(e => e.proposedBy?.length)) {
        // No provider call can support a mechanism whose required premises failed.
        if (edge.findingIds.some(id => state.findings.find(f => f.id === id)?.status !== 'supported')) {
          edge.status = 'unknown'; edge.reviewReason = 'One or more premises are unresolved; this connection remains a proposal.'; continue;
        }
        if (edge.status !== 'supported' || state.changedSourceIds.length)
          await add(state, 'verify', 'causal-verification', [edge.id], `${edge.rationale} ${edge.counterfactual} ${edge.alternative}`, edge.spanIds);
      }
    }
    if (phase === 7) {
      syncBoardEvidence(state);
      for (const direction of position.directions) {
        const q = state.questions.find(q => q.id === direction.questionId);
        if (q?.status === 'open') { q.status = 'awaiting-user'; q.reason ||= direction.evidenceNeeded; }
      }
      // Review gaps are retained as specifically targeted requests, never recursive work.
      for (const q of state.questions.filter(q => q.reviewTargets?.some(id => position.selectedFindingIds.includes(id)))) {
        if (q.status === 'open') q.status = 'awaiting-user';
      }
    }
    if (phase === 8) for (const p of state.propositions.filter(p => position.selectedFindingIds.includes(p.findingId) && p.status === 'supported' && p.humanStatus === 'accepted'
      && state.relationships.some(e => e.status === 'supported' && e.type !== 'preceded' && (e.from === p.id || e.to === p.id)))) {
      if (!state.actions.some(a => a.causalTargetIds.includes(p.id)))
        await add(state, 'actions', 'corrective-actions', [p.id], `${p.label} ${p.detail}`, p.spanIds);
    }
  }
}
