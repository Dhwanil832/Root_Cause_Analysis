import type { EngineInput, EngineSource, SourceSpan } from '@/src/engine/types';
import { digest } from '@/src/engine/identity';
import {validateReleasedInput} from '@/src/experiments/admission';

export const EXTRACTION_CONTRACT = 'lossless-offset-blocks-v1';
/** Lossless, offset-addressed blocks. Decimal points never delimit passages.
 * Table headers are repeated as CONTEXT, not fabricated into quoted source spans. */
export function textBlocks(text: string, size = 1800) {
  if (size < 64) throw new Error('A source block must accommodate at least 64 characters.');
  const blocks: Array<{ start: number; end: number; text: string; heading: string; tableHeader: string }> = [];
  let start = 0, heading = '', tableHeader = '';
  while (start < text.length) {
    let end = Math.min(text.length, start + size);
    if (end < text.length) {
      const line = text.lastIndexOf('\n', end);
      if (line > start + size / 3) end = line + 1;
    }
    const chunk = text.slice(start, end);
    const inheritedHeading = heading, inheritedHeader = tableHeader;
    const lines = chunk.split('\n');
    for (let i = 0; i < lines.length; i++) {
      if (/^#{1,6}\s/.test(lines[i])) { heading = lines[i]; tableHeader = ''; }
      if (lines[i].includes('|') && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1] || '')) tableHeader = lines[i] + '\n' + lines[i + 1];
    }
    blocks.push({ start, end, text: chunk, heading: inheritedHeading, tableHeader: inheritedHeader });
    start = end;
  }
  return blocks;
}

export async function registerSources(input: EngineInput, previous: EngineSource[] = []) {
  validateReleasedInput(input);
  const definitions: Array<{ id: string; text: string; revision: string; label: string; scope: SourceSpan['scope']; origin: SourceSpan['origin']; limitations: string[] }> = [
    { id: 'incident-description', text: input.incident, revision: '1', label: 'Original incident account', scope: 'incident', origin: 'incident-account', limitations: ['An incident account is not independent verification.'] },
    ...input.documents.map(d => ({ id: d.id, text: d.extractedText, revision: d.revision, label: d.title,
      scope: d.scope, origin: 'document' as const, limitations: d.extractionStatus === 'ready' ? [] : [`${d.extractionStatus}: ${d.extractionNotes}`] })),
    ...input.answers.map(a => ({ id: a.sourceId || `answer:${a.questionId}`, text: a.text, revision: a.answeredAt,
      label: `Answer to ${input.answerQuestions?.[a.questionId] || a.questionId}`, scope: 'answer' as const,
      origin: a.sourceId?.startsWith('story-release:') ? 'simulated-testimony' as const : 'user-answer' as const,
      limitations: [`Response status: ${a.responseStatus || 'answered'}. Testimony is not automatically verified.`] })),
  ];
  const sources: EngineSource[] = [], changed: string[] = [];
  for (const d of definitions) {
    const document = input.documents.find(doc => doc.id === d.id);
    const modality = document?.contentType.startsWith('image/') ? 'image' as const
      : document && !d.text.trim() && (document.contentType === 'application/pdf' || document.fileName.endsWith('.pdf')) ? 'file' as const : undefined;
    const textHash = await digest([EXTRACTION_CONTRACT, d.text, document?.sha256]);
    const prior = previous.find(p => p.id === d.id && p.revision === d.revision && p.textHash === textHash);
    if (prior) { sources.push(prior); continue; }
    changed.push(d.id);
    const spans: SourceSpan[] = textBlocks(d.text).map(block => ({ ...block, id: `span:${d.id}:${textHash.slice(0, 16)}:${block.start}-${block.end}`,
      sourceId: d.id, revision: d.revision, label: d.label, scope: d.scope, origin: d.origin }));
    if (modality) spans.push({id:`span:${d.id}:${textHash.slice(0,16)}:original`,sourceId:d.id,revision:d.revision,label:d.label,scope:d.scope,
      origin:d.origin,modality,start:0,end:0,text:'Original visual evidence attached separately. This marker is not a transcription or a factual observation.',heading:'',tableHeader:''});
    sources.push({ id: d.id, revision: d.revision, label: d.label, textHash, scope: d.scope, origin: d.origin, spans, limitations: d.limitations,
      questionId: document?.questionId || input.answers.find(a=>(a.sourceId || `answer:${a.questionId}`)===d.id)?.questionId });
  }
  changed.push(...previous.filter(p => !sources.some(s => s.id === p.id)).map(p => p.id));
  return { sources, changed: [...new Set(changed)] };
}

export function spanMap(sources: EngineSource[]) { return new Map(sources.flatMap(s => s.spans).map(s => [s.id, s])); }
export function exactCitation(span: SourceSpan) { return { sourceId: span.sourceId, label: span.modality ? `${span.label} [original ${span.modality}]` : `${span.label} [${span.start}:${span.end}]`,
  excerpt: span.modality ? 'Reference to the original visual evidence; not a verbatim text quotation.' : span.text }; }
