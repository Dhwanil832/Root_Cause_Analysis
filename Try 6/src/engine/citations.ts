import type { References } from './records';

/** Bind generated commentary at the call boundary, before S/F/Q aliases change.
 * Never call this on source passages or on the literal assertion under review.
 * Raw provider responses remain in the task trace for audit. */
export function bindCommentary(text: string, refs: References): string {
  return text.replace(/\b([SFQ]\d+)\b/g, (token) => {
    const map = token[0] === 'S' ? refs.sources : token[0] === 'F' ? refs.findings : refs.questions;
    const id = map.get(token);
    return id ? `⟦${token[0] === 'S' ? 'evidence' : token[0] === 'F' ? 'finding' : 'question'}:${id}⟧` : token;
  });
}
