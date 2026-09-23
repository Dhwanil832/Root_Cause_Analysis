import { z } from 'zod';
import type { ModelDescriptor, DocumentRecord } from '@/src/domain/types';
import type { SourceSpan } from '../types';
import type { EvidenceIndex } from '@/src/knowledge/retrieval/index';

export class TaskContextError extends Error { constructor(message: string) { super(message); this.name = 'TaskContextError'; } }
export const CONTEXT_POLICY = 'native-context-uncapped-output-v1';
export function contextCapacity(model: ModelDescriptor) {
  // Ollama descriptors carry the /api/show native window. A hosted provider
  // whose capacity is not reported owns admission; do not invent a 32K ceiling.
  if (model.contextWindow === undefined) return undefined;
  if (!Number.isSafeInteger(model.contextWindow) || model.contextWindow <= 0) throw new TaskContextError('Invalid model context configuration.');
  return model.contextWindow;
}
export const CONTEXT_OVERHEAD_TOKENS = 2048; // Template/schema wrappers; not an output cap.
export function inputByteCapacity(model: ModelDescriptor) {
  const capacity = contextCapacity(model);
  return capacity === undefined ? Infinity : Math.max(0, (capacity - CONTEXT_OVERHEAD_TOKENS - 1) * 2);
}
export function plannedBytes(system: string, packet: unknown, schema: z.ZodType) {
  return new TextEncoder().encode(system + JSON.stringify(packet) + JSON.stringify(z.toJSONSchema(schema, { target: 'draft-7' }))).length;
}
export function planContext(options: { model: ModelDescriptor; system: string; schema: z.ZodType; base: Record<string, unknown>;
  index: EvidenceIndex; query: string; required: string[]; onlyRequired?: boolean; numberEvidenceLines?: boolean;
  schemaForEvidence?: (spans: SourceSpan[]) => z.ZodType }) {
  const { model, system, schema, base, index } = options;
  const required = new Set(options.required);
  const missing = [...required].filter(id => !index.byId.has(id));
  if (missing.length) throw new TaskContextError(`Referenced source spans are missing: ${missing.join(', ')}`);
  // No fixed 32K ceiling, half/quarter-window quota or artificial generation
  // reserve. Original passages still have to fit the model's physical window.
  const capacity = contextCapacity(model), limit = inputByteCapacity(model);
  const chosen: SourceSpan[] = [], omitted: string[] = [];
  const contract = (spans: SourceSpan[]) => options.schemaForEvidence?.(spans) || schema;
  function packet(spans: SourceSpan[]) {
    return { ...base, evidence: spans.map((s, i) => ({ ref: `S${i + 1}`, label: s.label, scope: s.scope, origin: s.origin,
      offset: [s.start, s.end], heading: s.heading, tableHeaderContext: s.tableHeader,
      text: options.numberEvidenceLines ? s.text.split('\n').map((line,index)=>`${index+1}|${line}`).join('\n') : s.text,
      ...(options.numberEvidenceLines ? {lineNumbering:'One-based within this S passage. N| is a display prefix, not original text.'} : {}),
      ...(s.modality ? {modality:s.modality,attachmentDocumentId:s.sourceId} : {}) })),
      coverage: 'Selected original passages only. Unknown is not absence. Request additional evidence when a required premise is outside this working set.' };
  }
  if (plannedBytes(system, packet([]), contract([])) > limit) throw new TaskContextError('Task metadata alone exceeds the native-context estimate. Split targets; do not truncate history into a verdict.');
  const ranked=options.onlyRequired ? options.required.map(id=>index.byId.get(id)!) : index.ranked(options.query,options.required);
  for (const span of ranked) {
    const unsupported=span.modality && (model.provider==='ollama' ? span.modality==='file'||!model.capabilities?.includes('vision')
      : span.modality==='file'&&model.apiMode!=='responses');
    if(unsupported&&!required.has(span.id)){omitted.push(span.id);continue;}
    const candidate=[...chosen,span];
    const visualReservation=candidate.reduce((n,s)=>n+(s.modality==='image'?8192:s.modality==='file'?16384:0),0)*2;
    if (plannedBytes(system, packet(candidate), contract(candidate))+visualReservation <= limit) chosen.push(span);
    else if (required.has(span.id)) throw new TaskContextError('Required joint evidence exceeds the native-context estimate. Schedule smaller premise-reading tasks; no evidence was truncated.');
    else omitted.push(span.id);
  }
  const exactSchema = contract(chosen);
  const bytes=plannedBytes(system,packet(chosen),exactSchema);
  const mediaTokens=chosen.reduce((n,s)=>n+(s.modality==='image'?8192:s.modality==='file'?16384:0),0);
  return { packet: packet(chosen), schema: exactSchema, selected: chosen, omitted,
    references: new Map(chosen.map((s, i) => [`S${i + 1}`, s.id])),
    outputTokens:capacity === undefined ? undefined : Math.max(0,capacity-Math.ceil(bytes/2)-CONTEXT_OVERHEAD_TOKENS-mediaTokens),
    bytes, estimate: 'UTF-8 bytes / 2 plus template/media overhead; native context only when known. Output headroom is diagnostic, never a generation cap.' };
}

export function unreadDocuments(documents: DocumentRecord[]) { return documents.filter(d => d.extractionStatus !== 'ready' || !d.extractedText.trim()); }
