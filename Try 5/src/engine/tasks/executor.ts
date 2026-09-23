import { z } from 'zod';
import type { AgentId, ModelDescriptor, TagId } from '@/src/domain/types';
import { TAG_LABELS } from '@/src/domain/tag-catalog';
import { runProviderStage } from '@/src/providers';
import type { StageRequest, StageResponse, ModelMedia } from '@/src/providers/types';
import { schemas, taskSchema } from '../contracts';
import { taskPrompt } from '../prompts';
import { digest } from '../identity';
import { relatedFindings, type References } from '../records';
import { planContext,contextCapacity } from '../context/planner';
import { evidenceIndex } from '@/src/knowledge/retrieval/index';
import type { EngineState, EngineTask, EngineStore, TaskExecutorResult, TaskTrace } from '../types';
import { ENGINE_VERSION } from '../types';
import { STREAM_REPETITION_POLICY } from '@/src/providers/stream-repetition';
import { CLAIM_INTERPRETATION_POLICY } from '../review/contract';
import { CLAIM_REVIEW_POLICY } from '../review/literal-contract';
import { reviewInference } from '../review/inference-profile';

export type ProviderRunner = <T>(request: StageRequest<T>) => Promise<StageResponse<T>>;
export type MediaLoader = (sourceIds:string[])=>Promise<ModelMedia[]>;
const stageNames: Record<EngineTask['kind'], AgentId> = { read: 'evidence-reading', understand: 'incident-understanding', tag: 'tagging', specialist: 'other-novel',
  broker: 'question-broker', answer: 'answer-fetching', interpret: 'claim-interpretation', review: 'claim-review', causal: 'causal-analysis', inquiry:'causal-analysis', verify: 'causal-verification', actions: 'corrective-actions' };
export function taskBase(state: EngineState, task: EngineTask) {
  const refs: References = { sources: new Map(), findings: new Map(), questions: new Map() };
  const targets = state.findings.filter(f => task.targetIds.includes(f.id));
  const neighbors = ['causal','inquiry','specialist','answer'].includes(task.kind) ? relatedFindings(state, task.query, targets.map(f => f.id))
    .filter(f=>task.kind!=='specialist'||f.owners.includes(task.owner)||f.owners.includes('evidence-reading')).slice(0, 6) : [];
  const findings = [...targets, ...neighbors];
  findings.forEach((f, i) => refs.findings.set(`F${i + 1}`, f.id));
  const findingViews = findings.map((f, i) => ({ ref: `F${i + 1}`, statement: f.statement, kind: f.kind,
    subject: f.subject, predicate: f.predicate, location: f.location, time: f.time, unit: f.unit, qualifiers: f.qualifiers,
    evidenceStatus:f.status, interpretationOnly:true }));
  const base: Record<string, unknown> = { task: task.kind, owner: task.owner };
  // Original focal context is bounded by construction; never attach previous boards.
  if (!['read','review','interpret'].includes(task.kind)) base.incidentContext = { focalEvent: state.focalEvent, summary: state.summary };
  if (findingViews.length && !['review','interpret'].includes(task.kind)) base.findings = findingViews;
  // Do not prime an independent reviewer with the producer's kind, qualifiers,
  // prior approval or old call-local citations. Those are not original evidence.
  if(task.kind==='review'||task.kind==='interpret') base.target={statement:targets[0]?.statement};
  if(task.kind==='causal') base.target=findingViews[0];
  if(task.kind==='inquiry') {
    base.objective='Use this evidence neighborhood to distinguish plausible explanations and identify the most useful unresolved evidence requests.';
    base.targetReferences=[...refs.findings].filter(([,id])=>task.targetIds.includes(id)).map(([ref])=>ref);
    base.existingQuestions=state.questions.filter(q=>!q.coveredBy&&relatedQuestionScore(task.query,`${q.text} ${q.subject} ${q.location}`)>0)
      .map(q=>({text:q.text,status:q.status}));
  }
  if (task.kind === 'tag') base.taxonomy = TAG_LABELS;
  if (task.kind === 'specialist') {
    base.domain = TAG_LABELS[task.owner as TagId];
    base.targetReferences = [...refs.findings].filter(([,id]) => task.targetIds.includes(id)).map(([ref]) => ref);
  }
  if (task.kind === 'broker' || task.kind === 'answer') {
    const q = state.questions.find(q => q.id === task.targetIds[0]);
    if (!q) throw new Error('Unknown task question.');
    base.question = { text: q.text, intent: q.intent, decision: q.decision, subject: q.subject, location: q.location, time: q.time };
    if (task.kind === 'broker') {
      const candidates = state.questions.filter(other => other.id !== q.id && !other.coveredBy
        && state.questions.indexOf(other) < state.questions.indexOf(q))
        .map(other => ({ other, score: relatedQuestionScore(q.text, other.text) })).filter(c => c.score > 0)
        .sort((a, b) => b.score - a.score).slice(0, 6);
      candidates.forEach(({ other }, i) => refs.questions.set(`Q${i + 1}`, other.id));
      base.possibleDuplicates = candidates.map(({ other }, i) => ({ ref: `Q${i + 1}`, text: other.text, intent: other.intent,
        subject: other.subject, location: other.location, time: other.time, decision: other.decision }));
    }
  }
  if (task.kind === 'verify' || task.kind === 'actions') {
    const target = state.propositions.find(p => p.id === task.targetIds[0]) || state.relationships.find(e => e.id === task.targetIds[0]);
    if (!target) throw new Error('Unknown board target.');
    if(task.kind==='verify')base.verificationTarget='label' in target?'node':'relationship';
    base.target = 'label' in target ? { type: target.type, label: target.label, detail: target.detail }
      : { type: target.type, rationale: target.rationale, counterfactual: target.counterfactual, alternative: target.alternative, gap: target.gap,
        from: target.from === 'focal' ? state.focalEvent : state.propositions.find(p => p.id === target.from)?.label,
        to: target.to === 'focal' ? state.focalEvent : state.propositions.find(p => p.id === target.to)?.label };
  }
  return { base, refs };
}
function relatedQuestionScore(a: string, b: string) { const words = new Set(a.toLowerCase().split(/\W+/)); return b.toLowerCase().split(/\W+/).filter(w => w.length > 3 && words.has(w)).length; }

export async function executeTask(state: EngineState, task: EngineTask, model: ModelDescriptor, trackId: string,
  store: Pick<EngineStore, 'cached'>, runner: ProviderRunner = runProviderStage, mediaLoader?:MediaLoader,
  controls?: {signal?:AbortSignal;trace?:TaskTrace;thinking?:boolean;sampling?:StageRequest<unknown>['sampling']}): Promise<TaskExecutorResult & { refs: References }> {
  const verificationTarget=task.kind==='verify'
    ?state.propositions.some(p=>p.id===task.targetIds[0])?'node':'relationship':undefined;
  const system = taskPrompt(task.kind, task.owner, verificationTarget);
  const { base, refs } = taskBase(state, task);
  const index = evidenceIndex(trackId,state.sources);
  const target=state.findings.find(f=>task.targetIds.includes(f.id)),targetStatement=target?.statement || '';
  // Plan conservatively with the generic contract; build the exact enum grammar
  // only after selecting the original passages for this call.
  const context = planContext({ model, system, schema:schemas[task.kind], base, index, query: task.query, required: task.kind==='interpret'?[]:task.requiredSpanIds,
    onlyRequired:task.kind==='read'||task.kind==='interpret',numberEvidenceLines:task.kind==='review' });
  if(task.kind==='interpret')context.packet.coverage='Interpret wording only. No incident evidence or producer metadata is supplied.';
  refs.sources = context.references;
  const sourceLines=task.kind==='review' ? Object.fromEntries(context.selected.map((s,i)=>[`S${i+1}`,
    s.modality ? [] : s.text.split('\n').flatMap((line,n)=>line.trim()?[n+1]:[])])) : undefined;
  const schema=taskSchema(task.kind,[...refs.sources.keys()],[...refs.findings.keys()],[...refs.questions.keys()],targetStatement,sourceLines);
  // Exact grammar and target echo consume additional context too.
  const schemaDelta=Math.max(0,JSON.stringify(z.toJSONSchema(schema)).length-JSON.stringify(z.toJSONSchema(schemas[task.kind])).length);
  const outputTokens=context.outputTokens-Math.ceil(schemaDelta/2);
  if(outputTokens<1) throw new Error('Exact output contract exceeds available context; split the task before inference.');
  const negative = ['answer','review','causal','inquiry','verify'].includes(task.kind);
  // Diagnostics may explicitly compare another mode, but production uses the
  // declared model/stage profile. Both paths are visible in trace/cache identity.
  const inference=controls&&('thinking' in controls||'sampling' in controls)
    ?{thinking:controls.thinking??false,sampling:controls.sampling}:reviewInference(model,task.kind);
  const thinking=model.provider==='ollama'?inference.thinking:undefined;
  const identity = { engine: ENGINE_VERSION, streamPolicy: model.provider === 'ollama' ? STREAM_REPETITION_POLICY : undefined,
    reviewPolicy: task.kind === 'review' ? CLAIM_REVIEW_POLICY : undefined,
    ...(task.kind==='review'&&state.reviewFormattingPolicy?{reviewFormattingPolicy:state.reviewFormattingPolicy}:{}),
    interpretationPolicy: task.kind === 'interpret' ? CLAIM_INTERPRETATION_POLICY : undefined,
    kind: task.kind, owner: task.owner, system, schema: z.toJSONSchema(schema), packet: context.packet,
    model: { id: model.id, digest: model.digest, baseUrl: model.baseUrl, apiMode: model.apiMode },
    context: contextCapacity(model),thinking,sampling:inference.sampling,
    inventory: negative ? state.sources.map(s => `${s.id}:${s.textHash}`).sort() : undefined };
  const key = await digest(identity);
  await controls?.trace?.request({...identity,outputTokens:model.provider==='ollama'?-1:outputTokens,
    plannedAvailableOutputTokens:outputTokens,generationPolicy:model.provider==='ollama'?'until-provider-completion-no-application-cap':'provider-output-budget',
    estimate:context.estimate,selectedEvidence:context.selected.map(s=>s.id),omittedEvidence:context.omitted});
  const cache = model.provider === 'ollama' && !model.digest ? null : await store.cached(trackId, key);
  if (cache && schema.safeParse(cache.output).success) return { output: cache.output, refs, cacheKey: key, reused: true,
    evidenceIds: context.selected.map(s => s.id), omittedEvidenceIds: context.omitted, contextBytes: context.bytes, durationMs: 0, inputTokens: 0, outputTokens: 0 };
  // No inference is needed to keep a question that has no duplicate candidates.
  if (task.kind === 'broker' && !(base.possibleDuplicates as unknown[]).length) return {
    output: { equivalentTo: null, reason: 'No candidate duplicate in the indexed neighborhood.', decision: { summary: 'Kept distinct question.' } },
    refs, cacheKey: key, reused: false, evidenceIds: [], omittedEvidenceIds: [], contextBytes: 0, durationMs: 0, inputTokens: 0, outputTokens: 0,
  };
  if (task.kind === 'answer' && !context.selected.length) return {
    output: { status: 'not-found', answer: '', references: [], findings: [], evidenceRequest: 'No matching original passage was retrieved; please supply relevant evidence.', decision: { summary: 'Retrieval gap, not evidence of absence.' } },
    refs, cacheKey: key, reused: false, evidenceIds: [], omittedEvidenceIds: [], contextBytes: context.bytes, durationMs: 0, inputTokens: 0, outputTokens: 0,
  };
  const visual=context.selected.filter(s=>s.modality), media=visual.length&&mediaLoader ? await mediaLoader([...new Set(visual.map(s=>s.sourceId))]) : [];
  if (visual.some(s=>!media.some(m=>m.documentId===s.sourceId))) throw new Error('Original visual evidence could not be loaded. Supply readable text or a smaller supported file; the marker is not evidence.');
  if (media.length && model.provider==='ollama' && (!model.capabilities?.includes('vision') || media.some(m=>m.kind==='file')))
    throw new Error('This Ollama model cannot read the selected image/PDF originals. Use a vision-capable model track for images, or supply extracted text. No model fallback was used.');
  if (media.some(m=>m.kind==='file') && model.provider==='openai-compatible' && model.apiMode!=='responses')
    throw new Error('PDF original reading requires a compatible Responses file-input provider, or readable text.');
  const result = await runner({ stage: task.kind === 'specialist' ? task.owner as AgentId : stageNames[task.kind], model,
    systemPrompt: system, schema, schemaName: `try5_${task.kind}`, evidencePacket: context.packet,
    outputTokens, contextWindow: contextCapacity(model),thinking,sampling:inference.sampling,signal:controls?.signal,onChunk:controls?.trace?.append,
    noTruncation: true, maxAttempts: 1, media });
  // Non-streaming providers/test adapters still retain their full returned data.
  await controls?.trace?.complete('completed',{output:result.output,attempts:result.attempts,usage:result.usage});
  return { output: result.output, refs, cacheKey: key, reused: false, evidenceIds: context.selected.map(s => s.id),
    providerAttempts:result.attempts,
    omittedEvidenceIds: context.omitted, contextBytes: context.bytes, durationMs: result.durationMs,
    inputTokens: result.usage?.inputTokens || 0, outputTokens: result.usage?.outputTokens || 0 };
}
