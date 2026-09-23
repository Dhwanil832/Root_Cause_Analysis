import { frameSchema, consultSchema, resolveSchema, connectionSchema, responseSchema,revisionSchema,type directionSchema } from './contracts';
import type { z } from 'zod';
import { ingestQuestion, resolve, quarantine, type References } from '../records';
import type { EngineState, EngineTask, Finding } from '../types';
import { normalize, digest } from '../identity';
import { propositionId } from '../board/changes';
import { emptyPosition } from './types';
import { activeBoardFindings, hasUsablePosition } from './usability';
import {bindQuestion,mergeQuestions,queueDeliveries,receiveDelivery} from '../questions/ledger';
import {applyCorrections,applyImpacts} from '../revisions/apply';
import {refreshIntegrity} from '../validation/integrity';

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
  // Text and identity are different fields. Older outputs sometimes returned
  // a bare Q alias in question; bind it to this exact call's catalog, never
  // turn it into a new human-facing question or guess semantic equivalence.
  const alias=row.existingQuestion||(/^Q\d+$/.test(row.question.trim())?row.question.trim():null);
  const existingId=alias?refs.questions.get(alias):undefined;
  let existing=state.questions.find(q=>q.id===existingId);
  if(alias&&!existing)throw Error('Direction references an unknown existing question.');
  if(existing?.coveredBy)existing=state.questions.find(q=>q.id===existing!.coveredBy);
  if(alias&&!existing)throw Error('Existing question has no canonical target.');
  if(existing) {
    for(const field of ['subject','location','time'] as const)
      if(row[field].trim()&&normalize(row[field])!==normalize(existing[field]))throw Error(`Question reuse changes its ${field} scope; create a distinct request.`);
    if(row.question.trim()!==alias&&normalize(row.question)!==normalize(existing.text))throw Error('Question reuse cannot replace the original wording; create a distinct request.');
  }
  const parts=row.parts.map(part=>{
    const known=existing?.parts?.find(p=>p.id===part);
    if(known)return known.text;
    if(/:p\d+$/.test(part)||/^Q\d+$/.test(part)||part.includes('⟦'))throw Error('Question subpart must be readable text or a known subpart of its existing question.');
    return part;
  });
  if(!existing&&(/^Q\d+$/.test(row.question.trim())||row.question.includes('⟦question:')))throw Error('A new question requires readable wording, not an internal reference.');
  // Same normalized wording + decision is deterministic reuse, not a semantic merge.
  // Semantic merging is performed by the common resolver with explicit scope checks.
  let q = existing || state.questions.find(q => !q.coveredBy && normalize(q.text) === normalize(row.question) && normalize(q.decision) === normalize(row.decision)
    && normalize(q.subject)===normalize(row.subject)&&normalize(q.location)===normalize(row.location)&&normalize(q.time)===normalize(row.time)
    && normalize(q.intent)===normalize(row.evidenceNeeded));
  if (!q) {
    const id = ingestQuestion(state, task, { text: row.question, intent: row.evidenceNeeded, decision: row.decision,
      subject: row.subject, location: row.location, time: row.time, references: [] }, refs);
    q = state.questions.find(q => q.id === id)!;
  }
  q.owners = [...new Set([...q.owners, task.owner])];
  bindQuestion(q,task,{branchId:row.branch,decision:row.decision,evidenceNeeded:row.evidenceNeeded,ifPresent:row.ifPresent,ifAbsent:row.ifAbsent,parts});
  queueDeliveries(q);
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
    const jointConditions=resolve(row.jointConditions,refs.findings);
    if(jointConditions.length===1)throw Error('A joint condition group needs at least two distinct conditions.');
    const findingIds = [...new Set([fromId, toId, ...resolve(row.findings, refs.findings),...jointConditions].filter(id => id !== 'EVENT'))];
    if (facts(state, findingIds).some(f => f.kind === 'hypothesis')) throw new Error('A hypothesis cannot serve as an established premise for a causal connection. Keep it in an explanation branch.');
    const next = { id, from, to, type: row.type, rationale: row.rationale, counterfactual: row.counterfactual,
      alternative: row.alternative, gap: row.gap, spanIds: spans(state, findingIds), findingIds,
      jointConditions,proposedBy: ['investigation-map'], status: 'proposed' as const, reviewReason: '' };
    const prior = state.relationships.find(e => e.id === id);
    const changed = !prior || JSON.stringify([prior.rationale, prior.counterfactual, prior.alternative, prior.gap, prior.findingIds,prior.jointConditions]) !== JSON.stringify([next.rationale, next.counterfactual, next.alternative, next.gap, next.findingIds,next.jointConditions]);
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
  if(task.kind==='respond') {
    const out=responseSchema.parse(raw),seen=new Set<string>();
    attempts(state,task,out.responses,row=>{
      const id=refs.questions.get(row.question),q=state.questions.find(q=>q.id===id);
      if(!q||!task.targetIds.includes(q.id)||seen.has(q.id)||q.answerRevision!==row.answerRevision)throw Error('Answer response does not match its assigned revision.');
      receiveDelivery(q,task.owner,task.id,row.implication);seen.add(q.id);
    });
    for(const id of task.targetIds.filter(id=>!seen.has(id)))quarantine(state,task,{questionId:id},'Answer recipient omitted its impact response; delivery remains pending.');
    attempts(state,task,out.directions,row=>addDirection(state,task,row,refs));return;
  }
  if(task.kind==='revise') {
    const out=revisionSchema.parse(raw);
    const rejectedBefore=state.quarantine.length,priorSummary=state.summary;
    const corrected=applyCorrections(state,task,out,refs);
    await applyInvestigationTask(state,{...task,kind:'refine'}, {
      summary:out.summary || (out.corrections.length?'Summary pending reconciliation with corrected observations.':state.summary) || 'Provisional investigation.',
      focalEvent:state.focalEvent||'Reported incident',normalState:state.normalState,eventState:state.eventState,
      branches:out.branches,nodes:out.nodes,edges:[],tags:[],consultations:[],directions:out.directions,
      retiredNodes:out.retiredNodes,withdrawnEdges:out.withdrawnEdges,decision:out.decision,
    },refs);
    applyImpacts(state,task,out,refs,corrected);
    if(state.quarantine.length>rejectedBefore) {
      position.proposedNarrative={summary:out.summary,reason:out.decision.summary,taskId:task.id};
      state.summary=position.summary='Revision proposals were only partly admitted. Narrative reconciliation remains unresolved; use the current board, rejected-item record, and evidence-impact decisions.';
      position.revisionReason=`${corrected.size} of ${out.corrections.length} correction operations admitted; ${state.quarantine.length-rejectedBefore} proposed items rejected. The model narrative is retained separately, not presented as proof that its proposed changes occurred.`;
      state.changes.push({targetId:'investigation-summary',kind:'revised',reason:position.revisionReason,before:priorSummary,after:state.summary});
    }else delete position.proposedNarrative;
    return;
  }
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
    refreshIntegrity(state);
    syncBoardEvidence(state);
    return;
  }
  if (task.kind === 'resolve') {
    const out = resolveSchema.parse(raw), seen = new Set<string>();
    attempts(state, task, out.answers, row => {
      const id = refs.questions.get(row.question);
      if (!id || !task.targetIds.includes(id) || seen.has(id)) throw new Error('Answer must name one assigned question exactly once.');
      const q = state.questions.find(q => q.id === id)!;
      let evidence = resolve(row.references, refs.sources);
      const findingIds = resolve(row.findings, refs.findings);
      if (row.status === 'covered') {
        const otherId = row.equivalentTo && refs.questions.get(row.equivalentTo);
        const other = state.questions.find(q => q.id === otherId);
        if (!other || other.coveredBy || state.questions.indexOf(other) >= state.questions.indexOf(q)) throw new Error('Question coverage must point to an earlier canonical question; no cycles.');
        mergeQuestions(state,q,other,row.evidenceNeeded);
        seen.add(id);
        return;
      }
      if (row.equivalentTo) throw new Error('Only covered questions may name an equivalent question.');
      const coverage=row.coverage.map(c=>{
        if(!q.parts?.some(p=>p.id===c.part))throw Error('Coverage names an unknown question subpart.');
        const spanIds=resolve(c.references,refs.sources);
        if(['answered','partial','conflicting'].includes(c.status)&&(!spanIds.length||!c.answer.trim()))throw Error('Answered subparts require an original citation and answer.');
        return {partId:c.part,status:c.status,answer:c.answer,spanIds,gap:c.gap};
      });
      if(new Set(coverage.map(c=>c.partId)).size!==coverage.length)throw Error('Duplicate subpart coverage.');
      evidence=[...new Set([...evidence,...coverage.flatMap(c=>c.spanIds)])];
      const supportedAnswer = evidence.length > 0 && row.answer.trim().length > 0;
      q.status = row.status === 'answered' && supportedAnswer ? 'answered'
        : row.status === 'conflicting' && supportedAnswer ? 'conflicting'
        : row.status === 'partial' && supportedAnswer ? 'partial' : row.status==='unavailable'?'unavailable':'awaiting-user';
      // Older single-part outputs remain readable. Multi-part completeness
      // requires explicit coverage; an overall answered badge is insufficient.
      q.coverage=coverage.length?coverage:(q.parts?.length===1&&supportedAnswer?[{partId:q.parts[0].id,status:row.status==='conflicting'?'conflicting':row.status==='partial'?'partial':'answered',answer:row.answer,spanIds:evidence,gap:row.evidenceNeeded}]:[]);
      if(q.status==='answered'&&q.parts?.some(p=>!q.coverage?.some(c=>c.partId===p.id&&c.status==='answered')))q.status='partial';
      if(q.coverage.some(c=>c.status==='conflicting'))q.status='conflicting';
      q.answer = supportedAnswer ? row.answer : '';
      q.answerCompleteness = q.status === 'awaiting-user' ? 'not-found' : q.status;
      q.answerSpanIds = evidence; q.findingIds = findingIds;
      q.reason = row.evidenceNeeded || (q.status === 'awaiting-user' ? 'No supported answer in the searched evidence. Please supply the requested observation or record.' : 'Original evidence retrieved; not an independent causal verdict.');
      q.searchedSpanIds = [...refs.sources.values()];
      q.inventory = state.sources.map(s => `${s.id}:${s.textHash}`).sort().join('|');
      q.answerRevision=(q.answerRevision||0)+1;queueDeliveries(q);seen.add(id);
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
    attempts(state,task,out.alternatives,branch=> {
      const evidence=[...resolve(branch.supporting,refs.findings),...resolve(branch.opposing,refs.findings)];
      if(!evidence.length)throw Error('An alternative requires attributed observations.');
      if(!position.branches.some(b=>b.id===branch.id))position.branches.push({...branch,supporting:resolve(branch.supporting,refs.findings),opposing:resolve(branch.opposing,refs.findings),
        conditions:branch.conditions.map(c=>({...c,findings:resolve(c.findings,refs.findings)})),updatedVersion:state.version});
    });
    attempts(state, task, out.directions, row => {
      if (row.branch !== mission.branchId&&!out.alternatives.some(b=>b.id===row.branch)) throw new Error('Consultation direction needs an assigned or evidence-grounded alternative branch.');
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
    if(new Set(row.conditions.map(c=>c.id)).size!==row.conditions.length)throw Error('Condition IDs must be unique within an explanation.');
    for(const id of row.replaces)if(id===row.id||!position.branches.some(b=>b.id===id))throw Error('Branch lineage must name an existing different branch.');
    const supporting = resolve(row.supporting, refs.findings), opposing = resolve(row.opposing, refs.findings);
    const prior = position.branches.find(b => b.id === row.id);
    const conditions=row.conditions.map(c=>{
      const ids=resolve(c.findings,refs.findings);
      if(c.status==='established'&&(!ids.length||ids.some(id=>state.findings.find(f=>f.id===id)?.status!=='supported')))
        return {...c,status:'unknown' as const,findings:ids};
      return {...c,findings:ids};
    });
    const next = { ...row, supporting, opposing,conditions, updatedVersion: state.version };
    const before=prior?JSON.stringify(prior):undefined;
    if (prior) Object.assign(prior, next); else position.branches.push(next);
    for(const id of row.replaces) {
      const replaced=position.branches.find(b=>b.id===id)!;
      replaced.status='superseded';replaced.changeReason=row.changeReason;replaced.updatedVersion=state.version;
      state.changes.push({targetId:`branch:${id}`,kind:'revised',reason:`Superseded by ${row.id}: ${row.changeReason}`});
    }
    state.changes.push({ targetId: `branch:${row.id}`, kind: prior ? 'revised' : 'added', reason: row.changeReason,before,after:JSON.stringify(next),evidenceIds:spans(state,[...supporting,...opposing]) });
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
    else { if(prior.type!==row.type){delete prior.roleAssessment;if(prior.humanStatus==='accepted')prior.humanStatus='reopened';}prior.type = row.type; prior.label = f.statement; prior.spanIds = [...f.spanIds]; }
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

/** Literal support and role validity are independent gates. */
export function syncBoardEvidence(state: EngineState) {
  for (const p of state.propositions) {
    const f: Finding | undefined = state.findings.find(f => f.id === p.findingId);
    if (!f) continue;
    p.status = f.reviewExecution === 'complete' ? f.status : 'proposed';
    p.reviewReason = f.reviewReason || 'Source observation selected for the map; evidence check pending.';
    p.spanIds = [...f.spanIds]; p.label = f.statement; p.detail = '';
    if(p.roleAssessment&&(p.roleAssessment.findingRevision!==f.revision||p.roleAssessment.role!==p.type||f.reviewExecution!=='complete'))delete p.roleAssessment;
    if (p.humanStatus === 'accepted' && p.status !== 'supported') p.humanStatus = 'reopened';
  }
}
