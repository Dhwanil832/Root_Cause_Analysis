import { frameSchema, consultSchema, resolveSchema, connectionSchema, type directionSchema } from './contracts';
import type { z } from 'zod';
import { ingestQuestion, resolve, quarantine, type References } from '../records';
import type { EngineState, EngineTask, Finding } from '../types';
import { normalize, digest } from '../identity';
import { propositionId } from '../board/changes';
import { emptyPosition } from './types';
import { activeBoardFindings, hasUsablePosition } from './usability';

function facts(state: EngineState, ids: string[]) { return ids.flatMap(id => state.findings.find(f => f.id === id) || []); }
function spans(state: EngineState, ids: string[]) { return [...new Set(facts(state, ids).flatMap(f => f.spanIds))]; }
function requiredBranch(state: EngineState, id: string) {
  const branch = state.investigation!.branches.find(b => b.id === id);
  if (!branch) throw new Error(`Unknown investigation branch: ${id}`);
  return branch;
}
function addDirection(state: EngineState, task: EngineTask, row: z.infer<typeof directionSchema>, refs: References) {
  requiredBranch(state, row.branch);
  const findingIds = resolve(row.findings, refs.findings);
  // Same normalized wording + decision is deterministic reuse, not a semantic merge.
  // Semantic merging is performed by the common resolver with explicit scope checks.
  let q = state.questions.find(q => normalize(q.text) === normalize(row.question) && normalize(q.decision) === normalize(row.decision));
  if (!q) {
    const id = ingestQuestion(state, task, { text: row.question, intent: row.evidenceNeeded, decision: row.decision,
      subject: '', location: '', time: '', references: [] }, refs);
    q = state.questions.find(q => q.id === id)!;
  }
  q.owners = [...new Set([...q.owners, task.owner])];
  q.spanIds = [...new Set([...q.spanIds, ...spans(state, findingIds)])];
  const prior = state.investigation!.directions.find(d => d.questionId === q.id);
  if (prior) {
    prior.branchIds = [...new Set([...prior.branchIds, row.branch])];
  } else state.investigation!.directions.push({ questionId: q.id, branchIds: [row.branch], evidenceNeeded: row.evidenceNeeded,
    ifPresent: row.ifPresent, ifAbsent: row.ifAbsent, priority: row.priority });
  if (!q.answer) q.reason = row.evidenceNeeded;
}
function attempts<T>(state: EngineState, task: EngineTask, rows: T[], apply: (row: T) => void) {
  for (const row of rows) try { apply(row); } catch (error) { quarantine(state, task, row, error); }
}

function applyConnections(state: EngineState, task: EngineTask,
  out: Pick<z.infer<typeof connectionSchema>, 'edges' | 'withdrawnEdges'>, refs: References) {
  const position = state.investigation!;
  const endpoints = new Set(activeBoardFindings(state).map(f => f.id));
  for (const row of out.edges) try {
    const fromId = row.from === 'EVENT' ? 'EVENT' : resolve([row.from], refs.findings)[0];
    const toId = row.to === 'EVENT' ? 'EVENT' : resolve([row.to], refs.findings)[0];
    if (fromId === toId || [fromId, toId].some(id => id !== 'EVENT' && !endpoints.has(id)))
      throw new Error('Relationship endpoints must be distinct selected board nodes or EVENT.');
    if (row.type !== 'preceded' && (!row.counterfactual.trim() || !row.alternative.trim())) throw new Error('A causal proposal needs a counterfactual and alternative.');
    const from = fromId === 'EVENT' ? 'focal' : propositionId(fromId), to = toId === 'EVENT' ? 'focal' : propositionId(toId);
    const id = `${from}>${row.type}>${to}`;
    const findingIds = [...new Set([fromId, toId, ...resolve(row.findings, refs.findings)].filter(id => id !== 'EVENT'))];
    if (facts(state, findingIds).some(f => f.kind === 'hypothesis')) throw new Error('A hypothesis cannot serve as an established premise for a causal connection. Keep it in an explanation branch.');
    const next = { id, from, to, type: row.type, rationale: row.rationale, counterfactual: row.counterfactual,
      alternative: row.alternative, gap: row.gap, spanIds: spans(state, findingIds), findingIds,
      proposedBy: ['investigation-map'], status: 'proposed' as const, reviewReason: '' };
    const prior = state.relationships.find(e => e.id === id);
    const changed = !prior || JSON.stringify([prior.rationale, prior.counterfactual, prior.alternative, prior.gap, prior.findingIds]) !== JSON.stringify([next.rationale, next.counterfactual, next.alternative, next.gap, next.findingIds]);
    if (!prior) state.relationships.push(next);
    else if (changed || findingIds.some(id => position.changedFindingIds.includes(id))) Object.assign(prior, next);
    for (const id of findingIds) if (!position.selectedFindingIds.includes(id)) position.selectedFindingIds.push(id);
  } catch (error) {
    quarantine(state, task, row, error);
    (position.rejectedConnections ||= []).push({ taskId: task.id,
      fromFindingId: refs.findings.get(row.from) || row.from, toFindingId: refs.findings.get(row.to) || row.to,
      rationale: row.rationale, reason: error instanceof Error ? error.message : String(error) });
  }
  attempts(state, task, out.withdrawnEdges, row => {
    const edge = state.relationships.find(e => e.id === row.id);
    if (!edge) throw new Error('Cannot withdraw an unknown relationship.');
    edge.proposedBy = []; edge.status = 'unknown'; edge.reviewReason = row.reason;
    state.changes.push({ targetId: edge.id, kind: 'rejected', reason: row.reason });
  });
}

/** The notebook is never expanded by consultation, answer fetching or mapping. */
export async function applyInvestigationTask(state: EngineState, task: EngineTask, raw: unknown, refs: References) {
  const position = state.investigation ||= emptyPosition();
  if (task.kind === 'connect') {
    const out = connectionSchema.parse(raw);
    applyConnections(state, task, out, refs);
    attempts(state, task, out.nodeRequests, row => {
      const findingId = resolve([row.finding], refs.findings)[0];
      const f = state.findings.find(f => f.id === findingId);
      if (!f || f.kind === 'hypothesis' || !f.spanIds.length) throw new Error('A requested node must be a sourced observation.');
      if (!position.nodeRequests?.some(r => r.findingId === findingId && r.version === state.version))
        (position.nodeRequests ||= []).push({ findingId, reason: row.reason, taskId: task.id, version: state.version });
    });
    syncBoardEvidence(state);
    return;
  }
  if (task.kind === 'resolve') {
    const out = resolveSchema.parse(raw), seen = new Set<string>();
    attempts(state, task, out.answers, row => {
      const id = refs.questions.get(row.question);
      if (!id || !task.targetIds.includes(id) || seen.has(id)) throw new Error('Answer must name one assigned question exactly once.');
      seen.add(id);
      const q = state.questions.find(q => q.id === id)!;
      const evidence = resolve(row.references, refs.sources), findingIds = resolve(row.findings, refs.findings);
      if (row.status === 'covered') {
        const otherId = row.equivalentTo && refs.questions.get(row.equivalentTo);
        const other = state.questions.find(q => q.id === otherId);
        if (!other || other.coveredBy || state.questions.indexOf(other) >= state.questions.indexOf(q)) throw new Error('Question coverage must point to an earlier canonical question; no cycles.');
        q.coveredBy = other.id; q.status = 'covered'; q.reason = row.evidenceNeeded || 'Same scoped evidence decision; shared with earlier question.';
        other.owners = [...new Set([...other.owners, ...q.owners])];
        const ownDirection = position.directions.find(d => d.questionId === q.id), canonical = position.directions.find(d => d.questionId === other.id);
        if (canonical && ownDirection) canonical.branchIds = [...new Set([...canonical.branchIds, ...ownDirection.branchIds])];
        return;
      }
      if (row.equivalentTo) throw new Error('Only covered questions may name an equivalent question.');
      const supportedAnswer = evidence.length > 0 && row.answer.trim().length > 0;
      q.status = row.status === 'answered' && supportedAnswer ? 'answered'
        : row.status === 'conflicting' && supportedAnswer ? 'conflicting'
        : row.status === 'partial' && supportedAnswer ? 'partial' : 'awaiting-user';
      q.answer = supportedAnswer ? row.answer : '';
      q.answerCompleteness = q.status === 'awaiting-user' ? 'not-found' : row.status;
      q.answerSpanIds = evidence; q.findingIds = findingIds;
      q.reason = row.evidenceNeeded || (q.status === 'awaiting-user' ? 'No supported answer in the searched evidence. Please supply the requested observation or record.' : 'Original evidence retrieved; not an independent causal verdict.');
      q.searchedSpanIds = [...refs.sources.values()];
      q.inventory = state.sources.map(s => `${s.id}:${s.textHash}`).sort().join('|');
      // Shared answer belongs to all specialists that asked, not a new fact per owner.
      for (const f of facts(state, findingIds)) f.owners = [...new Set([...f.owners, ...q.owners])];
    });
    for (const id of task.targetIds.filter(id => !seen.has(id))) {
      const q = state.questions.find(q => q.id === id);
      if (q) { q.status = 'awaiting-user'; q.reason = 'Answer agent omitted this request; it remains unresolved.'; }
      quarantine(state, task, { questionId: id }, 'Answer agent omitted an assigned question.');
    }
    return;
  }
  if (task.kind === 'consult') {
    const out = consultSchema.parse(raw), mission = position.consultations.find(c => c.id === task.targetIds[0]);
    if (!mission) throw new Error('Specialist consultation missing.');
    const findingIds = resolve(out.findings, refs.findings);
    Object.assign(mission, { summary: out.summary, limitations: out.limitations, completedVersion: state.version });
    for (const f of facts(state, findingIds)) f.owners = [...new Set([...f.owners, mission.domain])];
    attempts(state, task, out.directions, row => {
      if (row.branch !== mission.branchId) throw new Error('Consultation direction is outside the assigned branch.');
      addDirection(state, task, row, refs);
    });
    return;
  }
  const out = frameSchema.parse(raw);
  if (!out.nodes.length && !out.branches.length && !position.branches.length && !out.directions.length)
    throw new Error('No usable investigative position: return source observations, a defensible explanation, or a concrete foundation evidence direction.');
  state.summary = out.summary; state.focalEvent = out.focalEvent; state.normalState = out.normalState; state.eventState = out.eventState;
  position.summary = out.summary; position.revisionReason = out.decision.summary;
  attempts(state, task, out.branches, row => {
    const supporting = resolve(row.supporting, refs.findings), opposing = resolve(row.opposing, refs.findings);
    const prior = position.branches.find(b => b.id === row.id);
    const next = { ...row, supporting, opposing, updatedVersion: state.version };
    if (prior) Object.assign(prior, next); else position.branches.push(next);
    state.changes.push({ targetId: `branch:${row.id}`, kind: prior ? 'revised' : 'added', reason: row.changeReason });
  });
  for (const prior of position.branches.filter(b => !out.branches.some(b2 => b.id === b2.id)))
    state.changes.push({ targetId: `branch:${prior.id}`, kind: 'retained', reason: 'Prior branch omitted by model; retained, not silently closed.' });
  attempts(state, task, out.nodes, row => {
    const id = resolve([row.finding], refs.findings)[0], f = state.findings.find(f => f.id === id)!;
    if (f.kind === 'hypothesis' || !f.spanIds.length) throw new Error('Hypotheses belong in explanation branches, not factual board nodes.');
    if (!position.selectedFindingIds.includes(id)) position.selectedFindingIds.push(id);
    const prior = state.propositions.find(p => p.findingId === id);
    if (!prior) state.propositions.push({ id: propositionId(id), findingId: id, type: row.type, label: f.statement, detail: '',
      spanIds: [...f.spanIds], status: 'proposed', reviewReason: row.reason, humanStatus: 'unreviewed' });
    else { prior.type = row.type; prior.label = f.statement; prior.spanIds = [...f.spanIds]; }
  });
  // Legacy saved frames can contain edges; new frame/refine grammars require [].
  applyConnections(state, task, out, refs);
  attempts(state, task, out.retiredNodes, row => {
    const id = resolve([row.finding], refs.findings)[0];
    if (out.nodes.some(n => n.finding === row.finding)) throw new Error('A node cannot be selected and retired in the same proposal.');
    if (state.relationships.some(e => e.proposedBy?.length && e.findingIds.includes(id))) throw new Error('Withdraw dependent connections before retiring a premise.');
    position.selectedFindingIds = position.selectedFindingIds.filter(f => f !== id);
    state.changes.push({ targetId: propositionId(id), kind: 'rejected', reason: row.reason });
  });
  attempts(state, task, out.tags, row => {
    const findingIds = resolve(row.findings, refs.findings), spanIds = spans(state, findingIds);
    const prior = state.tags.find(t => t.id === row.id);
    if (prior) Object.assign(prior, { reason: row.reason, spanIds }); else state.tags.push({ id: row.id, reason: row.reason, spanIds });
    for (const f of facts(state, findingIds)) f.tags = [...new Set([...f.tags, row.id])];
  });
  attempts(state, task, out.directions, row => addDirection(state, task, row, refs));
  // The consolidation may suggest future expertise, but cannot recursively launch it.
  if (task.kind === 'frame') for (const row of out.consultations) try {
    const branch = requiredBranch(state, row.branch), findingIds = resolve(row.findings, refs.findings);
    const fingerprint = await digest([row.domain, row.purpose, branch.mechanism, branch.gap,
      facts(state, [...new Set([...findingIds, ...branch.supporting, ...branch.opposing])]).map(f => [f.id, f.revision])]);
    if (!position.consultations.some(c => c.fingerprint === fingerprint)) position.consultations.push({
      id: `consult:${fingerprint}`, branchId: branch.id, domain: row.domain, purpose: row.purpose,
      findingIds, fingerprint, summary: '', limitations: '',
    });
  } catch (error) { quarantine(state, task, row, error); }
  if (!hasUsablePosition(state)) throw new Error('No usable investigative position survived validation.');
  syncBoardEvidence(state);
}

/** Literal review is the node's evidence gate. There is no second node rewrite/review. */
export function syncBoardEvidence(state: EngineState) {
  for (const p of state.propositions) {
    const f: Finding | undefined = state.findings.find(f => f.id === p.findingId);
    if (!f) continue;
    p.status = f.reviewExecution === 'complete' ? f.status : 'proposed';
    p.reviewReason = f.reviewReason || 'Source observation selected for the map; evidence check pending.';
    p.spanIds = [...f.spanIds]; p.label = f.statement; p.detail = '';
    if (p.humanStatus === 'accepted' && p.status !== 'supported') p.humanStatus = 'reopened';
  }
}
