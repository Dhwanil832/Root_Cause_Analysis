import { z } from 'zod';
import type { ModelDescriptor, DocumentRecord } from '@/src/domain/types';
import type { SourceSpan } from '../types';
import type { EvidenceIndex } from '@/src/knowledge/retrieval/index';

export class TaskContextError extends Error { constructor(message: string) { super(message); this.name = 'TaskContextError'; } }
export function contextCapacity(model: ModelDescriptor) {
  const value = Number(model.contextWindow || (model.provider === 'ollama' ? process.env.OLLAMA_CONTEXT_LENGTH || 32768 : process.env.API_CONTEXT_LENGTH || 32768));
  if (!Number.isFinite(value) || value < 4096) throw new TaskContextError('Invalid model context configuration.');
  return value;
}
export function plannedBytes(system: string, packet: unknown, schema: z.ZodType) {
  return new TextEncoder().encode(system + JSON.stringify(packet) + JSON.stringify(z.toJSONSchema(schema, { target: 'draft-7' }))).length;
}
export function planContext(options: { model: ModelDescriptor; system: string; schema: z.ZodType; base: Record<string, unknown>;
  index: EvidenceIndex; query: string; required: string[]; outputTokens?: number; onlyRequired?: boolean; numberEvidenceLines?: boolean }) {
  const { model, system, schema, base, index } = options;
  const required = new Set(options.required);
  const missing = [...required].filter(id => !index.byId.has(id));
  if (missing.length) throw new TaskContextError(`Referenced source spans are missing: ${missing.join(', ')}`);
  // Reserve room for generation, then give the model ALL remaining usable
  // capacity after assembling its focused input. This is not a 3,200-token cap.
  const reserve = options.outputTokens ?? Math.floor(contextCapacity(model)/2);
  const limit = Math.max(0, (contextCapacity(model) - reserve - 2048) * 2);
  const chosen: SourceSpan[] = [], omitted: string[] = [];
  function packet(spans: SourceSpan[]) {
    return { ...base, evidence: spans.map((s, i) => ({ ref: `S${i + 1}`, label: s.label, scope: s.scope, origin: s.origin,
      offset: [s.start, s.end], heading: s.heading, tableHeaderContext: s.tableHeader,
      text: options.numberEvidenceLines ? s.text.split('\n').map((line,index)=>`${index+1}|${line}`).join('\n') : s.text,
      ...(options.numberEvidenceLines ? {lineNumbering:'One-based within this S passage. N| is a display prefix, not original text.'} : {}),
      ...(s.modality ? {modality:s.modality,attachmentDocumentId:s.sourceId} : {}) })),
      coverage: 'Selected original passages only. Unknown is not absence. Request additional evidence when a required premise is outside this working set.' };
  }
  if (plannedBytes(system, packet([]), schema) > limit) throw new TaskContextError('Task metadata alone exceeds the context allowance. Split targets; do not truncate history into a verdict.');
  const ranked=options.onlyRequired ? options.required.map(id=>index.byId.get(id)!) : index.ranked(options.query,options.required);
  for (const span of ranked) {
    const unsupported=span.modality && (model.provider==='ollama' ? span.modality==='file'||!model.capabilities?.includes('vision')
      : span.modality==='file'&&model.apiMode!=='responses');
    if(unsupported&&!required.has(span.id)){omitted.push(span.id);continue;}
    const candidate=[...chosen,span];
    const visualReservation=candidate.reduce((n,s)=>n+(s.modality==='image'?8192:s.modality==='file'?16384:0),0)*2;
    if (plannedBytes(system, packet(candidate), schema)+visualReservation <= limit) chosen.push(span);
    else if (required.has(span.id)) throw new TaskContextError('Required joint evidence exceeds this task allowance. Schedule smaller premise-reading tasks; no evidence was truncated.');
    else omitted.push(span.id);
  }
  const bytes=plannedBytes(system,packet(chosen),schema);
  const mediaTokens=chosen.reduce((n,s)=>n+(s.modality==='image'?8192:s.modality==='file'?16384:0),0);
  return { packet: packet(chosen), selected: chosen, omitted,
    references: new Map(chosen.map((s, i) => [`S${i + 1}`, s.id])),
    outputTokens:Math.max(1,contextCapacity(model)-Math.ceil(bytes/2)-2048-mediaTokens),
    bytes, estimate: 'UTF-8 bytes / 2 with explicit output and overhead reservation' };
}

export function unreadDocuments(documents: DocumentRecord[]) { return documents.filter(d => d.extractionStatus !== 'ready' || !d.extractedText.trim()); }
