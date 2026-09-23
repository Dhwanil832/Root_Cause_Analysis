// Retained for historical comparison only. Try 6 dispatches investigation/planner.
import { digest, overlap } from '../identity';
import type { EngineInput, EngineState, EngineTask, TaskKind } from '../types';
import { registerSources } from '@/src/knowledge/sources/registry';
import { findingText } from '../records';
import { TAG_LABELS } from '@/src/domain/tag-catalog';
import { reconcileAnswers } from '@/src/stages/question-broker/task';
import { invalidateReview } from '../review/interpretation';
import { CLAIM_INTERPRETATION_POLICY } from '../review/contract';
import { CLAIM_REVIEW_POLICY } from '../review/literal-contract';

export async function initializeState(input: EngineInput, version: number, previous: EngineState | null): Promise<EngineState> {
  const registered = await registerSources(input, previous?.sources);
  const state: EngineState = previous ? structuredClone(previous) : {
    version, phase: 0, initialized: true, sources: [], changedSourceIds: [], findings: [], questions: [], propositions: [],
    relationships: [], tags: [], summary: '', focalEvent: '', normalState: '', eventState: '', entities: [], tasks: [],
    quarantine: [], changes: [], decisions: [], actions: [],
  };
  Object.assign(state, { version, phase: 0, initialized: true, sources: registered.sources, changedSourceIds: registered.changed,
    tasks: [], quarantine: [], changes: [], followupPass: false, pauseReason:'', pauseAfterTaskId:undefined, readingApproved:false, reviewAfterReading:input.reviewAfterReading,
    progressiveBoard:true,reviewFormattingPolicy:input.reviewFormattingPolicy });
  // A fresh input revision already names its engine. The old execution's
  // migration lineage must not override the new revision's identity.
  delete state.executionMigrations;
  const valid = new Set(state.sources.flatMap(s => s.spans.map(p => p.id)));
  for (const finding of state.findings) if ([...finding.spanIds,...(finding.reviewAssessment?.parts.flatMap(p=>p.spanIds)||[])].some(id => !valid.has(id))) {
    invalidateReview(finding,'unreviewed','A cited source was revised or removed; this finding requires rechecking.',state);
    finding.spanIds = finding.spanIds.filter(id => valid.has(id));
    delete finding.reviewAssessment; delete finding.causalRole; delete finding.causalRelevance;
  }
  for (const q of state.questions) {
    const lost=q.answerSpanIds.some(id=>!valid.has(id));
    q.spanIds = q.spanIds.filter(id => valid.has(id)); q.answerSpanIds = q.answerSpanIds.filter(id => valid.has(id));
    if(lost&&!q.coveredBy) {
      q.status='awaiting-user';q.answer='';q.answerCompleteness='not-found';q.inventory='';
      q.coverage=q.coverage?.map(c=>c.spanIds.some(id=>!valid.has(id))?{...c,status:'not-found',answer:'',spanIds:[],gap:'Original supporting evidence was revised or withdrawn.'}:c);
      q.reason='Supporting evidence was revised or withdrawn; answer coverage must be reassessed.';
    }
  }
  for (const p of [...state.propositions, ...state.relationships]) p.spanIds = p.spanIds.filter(id => valid.has(id));
  if (input.humanDecision) {
    const decision = input.humanDecision;
    state.decisions.push(decision);
    const target = state.propositions.find(p => p.id === decision.targetId);
    if (target) target.humanStatus = ['accept', 'approve'].includes(decision.action) ? 'accepted' : 'rejected';
    const observation=state.findings.find(f=>f.id===decision.targetId);
    if(observation && decision.targetType==='document-observation') observation.humanStatus=['accept','approve'].includes(decision.action)?'accepted':'rejected';
    const action = state.actions.find(a => a.id === decision.targetId);
    if (action) action.status = ['accept', 'approve'].includes(decision.action) ? 'accepted' : 'proposed';
    state.changes.push({ targetId: decision.targetId, kind: 'revised', reason: `Human ${decision.action}: ${decision.notes}` });
    // Human decisions do not magically alter machine evidence verdicts.
    if (!registered.changed.length) state.phase = 9;
  }
  return state;
}

function chunks<T>(items: T[], count: number) { const pages: T[][] = []; for (let i = 0; i < items.length; i += count) pages.push(items.slice(i, i + count)); return pages; }
async function add(state: EngineState, kind: TaskKind, owner: string, ids: string[], query: string, required: string[] = [], progressive=false) {
  const policy=kind==='interpret'?CLAIM_INTERPRETATION_POLICY:kind==='review'?CLAIM_REVIEW_POLICY:undefined;
  const targetRevision=['review','causal','interpret'].includes(kind)&&ids.length===1?state.findings.find(f=>f.id===ids[0])?.revision:undefined;
  // Formatting policy versions the call cache, not the unit of work. Enabling
  // it must not schedule duplicates of already completed reviews.
  const id = await digest([kind, owner, ids, query, required,targetRevision,...(policy?[policy]:[])]);
  if (state.tasks.some(t => t.id === id)) return;
  const prerequisites:Partial<Record<TaskKind,TaskKind[]>>={tag:['read'],specialist:['tag'],answer:['broker'],interpret:['read','specialist','answer'],review:['read','specialist','answer'],causal:['review'],verify:['causal'],actions:['verify']};
  // Actual producers/verifiers of these targets, never every task that happened
  // to retrieve the same source passage (the old quadratic dependency fan-out).
  const dependsOn=state.tasks.filter(t=>(prerequisites[kind]||[]).includes(t.kind)
    && (!progressive || t.status==='completed')
    && [...t.targetIds,...(t.producedIds||[])].some(id=>ids.includes(id))).map(t=>t.id);
  state.tasks.push({ id, kind, owner, targetIds: ids, query, requiredSpanIds: [...new Set(required)], dependsOn,
    targetRevision,...(progressive?{priority:'board' as const}:{}),
    status: 'queued', attempts: 0, cacheKey: '', error: '', reused: false, evidenceIds: [], omittedEvidenceIds: [],
    contextBytes: 0, durationMs: 0, inputTokens: 0, outputTokens: 0, createdAt: new Date().toISOString() });
}
function changedText(state: EngineState) { return state.sources.filter(s => state.changedSourceIds.includes(s.id)).flatMap(s => s.spans).map(s => s.text).join('\n'); }
function relevant(state: EngineState, query: string, spans: string[]) {
  if (state.version === 1) return true;
  const changed = state.sources.filter(s => state.changedSourceIds.includes(s.id));
  if (!changed.length) return false;
  if (changed.some(s => s.spans.some(p => spans.includes(p.id)))) return true;
  // Unknown-domain evidence is conservatively invalidating. Once reading tags it,
  // source/domain overlap supplements lexical retrieval (negation and synonyms).
  const newFindings = state.findings.filter(f => f.spanIds.some(id => changed.some(s => s.spans.some(p => p.id === id))));
  if (!newFindings.length || newFindings.some(f => !f.tags.length)) return true;
  const targetTags = state.findings.filter(f => f.spanIds.some(id => spans.includes(id))).flatMap(f => f.tags);
  if (newFindings.some(f => f.tags.some(tag => targetTags.includes(tag)))) return true;
  return overlap(query, changedText(state)) > 0;
}

/** Advance phase barriers only after each independent unit is terminal. A failed
 * unit is visible and does not stop siblings; final status remains partial. */
export async function planNext(state: EngineState) {
  if(state.pauseReason) return null;
  // Publish provisional board progress from original-source findings without
  // waiting for every specialist. This is scheduling, not relaxed evidence gates:
  // each node still requires literal claim review, causal mapping and verification.
  // Later statement/evidence edits invalidate support through the existing ledger.
  if(state.progressiveBoard && state.phase>=4 && state.phase<=6 && !state.pauseAfterTaskId
    && !state.tasks.some(t=>['read','understand','tag'].includes(t.kind)&&t.status!=='completed')) {
    const score=(f:EngineState['findings'][number])=>(f.kind==='measurement'?20:0)+overlap(state.focalEvent,findingText(f));
    const candidates=state.findings.filter(f=>f.owners.includes('evidence-reading')
      && ['observation','measurement','testimony'].includes(f.kind) && score(f)>0)
      .sort((a,b)=>score(b)-score(a)||a.id.localeCompare(b.id));
    const taskFor=(kind:TaskKind,id:string,revision?:number)=>[...state.tasks].reverse().find(t=>t.kind===kind&&t.targetIds.includes(id)
      && (revision===undefined||t.targetRevision===revision));
    for(const f of candidates) {
      let task=taskFor('review',f.id,f.revision);
      if(!task) {await add(state,'review','claim-review',[f.id],findingText(f),f.spanIds,true);task=state.tasks.at(-1);}
      if(task?.status==='queued' && task.dependsOn.every(id=>state.tasks.some(t=>t.id===id&&t.status==='completed')))return task;
      if(task?.status!=='completed'||f.reviewExecution!=='complete'||f.status!=='supported')continue;
      task=taskFor('causal',f.id,f.revision);
      if(!task) {await add(state,'causal','causal-analysis',[f.id],findingText(f),f.spanIds,true);task=state.tasks.at(-1);}
      if(task?.status==='queued' && task.dependsOn.every(id=>state.tasks.some(t=>t.id===id&&t.status==='completed')))return task;
      if(task?.status!=='completed')continue;
      const node=state.propositions.find(p=>p.findingId===f.id);
      if(node) {
        task=taskFor('verify',node.id);
        if(!task){await add(state,'verify','causal-verification',[node.id],`${node.label} ${node.detail}`,node.spanIds,true);task=state.tasks.at(-1);}
        if(task?.status==='queued'&&task.dependsOn.every(id=>state.tasks.some(t=>t.id===id&&t.status==='completed')))return task;
      }
    }
  }
  while (!state.tasks.some(t => t.status === 'queued' || t.status === 'running') && state.phase < 10) {
    const failedFoundation=state.tasks.find(t=>['read','understand','tag'].includes(t.kind)&&['failed','blocked'].includes(t.status));
    if(failedFoundation) {state.pauseReason=`Prerequisite ${failedFoundation.kind} failed: ${failedFoundation.error}`;return null;}
    if(state.phase===1&&state.reviewAfterReading&&!state.readingApproved) {
      state.pauseReason='Evidence-reading checkpoint: original-document findings are ready for inspection. Approve/resume to begin interpretation.';return null;
    }
    const phase = state.phase++;
    if (phase === 0) for (const source of state.sources) {
      for (const page of chunks(source.spans, 1)) await add(state, 'read', 'evidence-reading', page.map(s => s.id), source.label, page.map(s => s.id));
      if (!source.spans.length) {
        await add(state, 'read', 'evidence-reading', [source.id], source.label);
        const task = state.tasks.at(-1)!; task.status = 'blocked'; task.error = `No readable extraction for ${source.label}. Supply readable text or supported visual evidence.`;
      }
    }
    if (phase === 1) {
      // Focused understanding uses the incident's own spans. No derived full-board packet.
      const incident = state.sources.find(s => s.scope === 'incident');
      for (const page of chunks(incident?.spans || [], 3)) await add(state, 'understand', 'baseline', page.map(s => s.id), page.map(s => s.text).join('\n'), page.map(s => s.id));
    }
    if (phase === 2) for (const page of chunks(state.findings, 6)) await add(state, 'tag', 'tagging', page.map(f => f.id), page.map(findingText).join('\n'));
    if (phase === 3) for (const tag of state.tags) {
      const candidates = state.findings.filter(f => f.tags.includes(tag.id));
      for (const page of chunks(candidates.length ? candidates : state.findings.filter(f => f.spanIds.some(s => tag.spanIds.includes(s))), 5)) {
        const query = `${TAG_LABELS[tag.id]} ${page.map(findingText).join('\n')}`;
        if (state.version === 1 || page.some(f => f.updatedVersion === state.version) || relevant(state, query, page.flatMap(f => f.spanIds))) {
          await add(state, 'specialist', tag.id, page.map(f => f.id), query);
        }
      }
    }
    if (phase === 4) for (const q of state.questions.filter(q => !q.coveredBy)) await add(state, 'broker', 'question-broker', [q.id], `${q.text} ${q.subject} ${q.location} ${q.time}`);
    if (phase === 5) for (const q of state.questions.filter(q => !q.coveredBy)) {
      // Negative results depend on the inventory; successful answers on relevant changes.
      if (q.status !== 'answered' || relevant(state, `${q.text} ${q.subject} ${q.location}`, q.answerSpanIds))
        await add(state, 'answer', 'answer-fetching', [q.id], `${q.text} ${q.intent} ${q.subject} ${q.location} ${q.time}`,
          [...q.spanIds,...state.sources.filter(s=>s.questionId===q.id).flatMap(s=>s.spans.map(p=>p.id))]);
    }
    if (phase === 6) for (const f of state.findings) {
      if(f.reviewExecution==='complete'&&state.tasks.some(t=>t.kind==='review'&&t.targetIds.includes(f.id)&&t.targetRevision===f.revision&&t.status==='completed'))continue;
      if (f.status !== 'supported' || f.reviewAssessment?.policy!==CLAIM_REVIEW_POLICY || f.updatedVersion === state.version || relevant(state, findingText(f), f.spanIds)) {
        await add(state, 'review', 'claim-review', [f.id], findingText(f), f.spanIds);
      }
    }
    if (phase === 7) {
      reconcileAnswers(state);
      // A record observation may constrain competing explanations. The reviewer's
      // scope label must not silently remove it from subsequent investigation.
      for (const f of state.findings) if (f.kind !== 'context'
        && state.tasks.some(t=>t.kind==='review'&&t.targetIds.includes(f.id)&&t.status==='completed')
        && (f.updatedVersion === state.version || relevant(state, findingText(f), f.spanIds)
        || !state.propositions.some(p => p.findingId === f.id))) await add(state, 'causal', 'causal-analysis', [f.id], findingText(f), f.spanIds);
    }
    if (phase === 8) {
      const nodeIds = new Set(['focal', ...state.propositions.map(p => p.id)]);
      for (const edge of state.relationships) if (!nodeIds.has(edge.from) || !nodeIds.has(edge.to)) {
        edge.status = 'unknown'; edge.reviewReason = 'An endpoint is not a causal proposition; this is an unresolved proposal, not an active causal link.';
      }
      for (const target of [...state.propositions, ...state.relationships.filter(e => nodeIds.has(e.from) && nodeIds.has(e.to) && e.proposedBy?.length)]) {
        const query = 'label' in target ? `${target.label} ${target.detail}` : `${target.rationale} ${target.counterfactual} ${target.alternative}`;
        if (target.status !== 'supported' || relevant(state, query, target.spanIds)) await add(state, 'verify', 'causal-verification', [target.id], query, target.spanIds);
      }
    }
    if (phase === 9) {
      // No fixed follow-up-round cap. Task identity prevents retrying a question
      // against the same evidence; only unprocessed questions enter another pass.
      const late = state.questions.filter(q => !q.coveredBy && !state.tasks.some(t => t.kind === 'broker' && t.targetIds.includes(q.id)));
      if (late.length) {
        state.followupPass = true;
        for (const q of late) await add(state, 'broker', 'question-broker', [q.id], `${q.text} ${q.subject} ${q.location} ${q.time}`);
        state.phase = 5;
      } else {
        for (const p of state.propositions.filter(p => p.status === 'supported' && p.humanStatus === 'accepted'
          && state.relationships.some(e => e.status === 'supported' && e.type !== 'preceded' && (e.from === p.id || e.to === p.id))))
          if (!state.actions.some(a => a.causalTargetIds.includes(p.id))) await add(state, 'actions', 'corrective-actions', [p.id], `${p.label} ${p.detail}`, p.spanIds);
      }
    }
    // Re-enter priority selection after scheduling the first specialist batch.
    // The phase has advanced, so this transition cannot recurse indefinitely.
    if(phase===3&&state.progressiveBoard)return planNext(state);
  }
  for(const t of state.tasks.filter(t=>t.status==='queued')) {
    const deps=t.dependsOn.map(id=>state.tasks.find(other=>other.id===id));
    if(deps.some(d=>!d||d.status==='failed'||d.status==='blocked')) {
      t.status='blocked';t.error='A required producer/reviewer failed; no dependent inference was run.';
    }
  }
  const next=state.tasks.find(t => t.status === 'queued' && (!state.pauseAfterTaskId || t.id === state.pauseAfterTaskId)
    && t.dependsOn.every(id=>state.tasks.some(d=>d.id===id&&d.status==='completed')));
  if (!next && state.pauseAfterTaskId) {
    state.pauseReason = 'Selected recovery task is not runnable; no other task was started.';
    return null;
  }
  if(!next&&state.phase<10&&!state.tasks.some(t=>t.status==='queued'||t.status==='running'))return planNext(state);
  if(!next&&state.tasks.some(t=>t.status==='queued'))state.pauseReason='No runnable task: unresolved dependency. Inspect the saved plan before continuing.';
  return next || null;
}

export function currentTask(state: EngineState): EngineTask | undefined { return state.tasks.find(t => t.status === 'running'); }
