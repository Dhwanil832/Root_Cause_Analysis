import { VERIFICATION_PACKET_TARGET_CHARACTERS } from '../../knowledge/packet-limits';

const CONTEXT_FIELDS = ['claims', 'sources', 'answers', 'conflicts'] as const;

/** Prefer manageable serialized input, without a hard size-based failure.
 * Fitting packets remain byte-for-byte equivalent for checkpoint reuse.
 * Oversized packets retain every target and node; only context collections
 * are partitioned. Every partition is reviewed, with conservative aggregation
 * in run.ts. No record, quotation or text prefix is silently discarded.
 */
export function verificationPacketPartitions<T extends {
  claims: unknown[]; sources: unknown[]; answers: unknown; conflicts: unknown;
}>(packet: T): T[] {
  if (JSON.stringify(packet).length <= VERIFICATION_PACKET_TARGET_CHARACTERS) return [packet];
  const originalCounts = Object.fromEntries(CONTEXT_FIELDS.map(field =>
    [field, Array.isArray(packet[field]) ? packet[field].length : null]));
  const coverage = (page: number, pages: number) => ({
    page, pages, originalCounts,
    instruction: 'This is one partition of the verification context. All targets are reviewed across every partition. Missing claims, sources, answers or conflicts on this page do not establish absence. Context may repeat across pages. Claim reviews are not independent corroboration.',
  });
  const annotate = (part: T, page: number, pages: number): T => ({
    ...part, verificationContext: coverage(page, pages),
  });
  const parts: T[] = [];
  function split(part: T) {
    // Reserve the largest possible page-counter representation before sizing.
    if (JSON.stringify(annotate(part, Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER)).length <= VERIFICATION_PACKET_TARGET_CHARACTERS) {
      parts.push(part);
      return;
    }
    const field = CONTEXT_FIELDS.filter(key => Array.isArray(part[key]) && part[key].length > 1)
      .sort((a, b) => JSON.stringify(part[b]).length - JSON.stringify(part[a]).length)[0];
    if (!field) {
      // Keep the complete record/target even when it exceeds the preferred size.
      parts.push(part);
      return;
    }
    const items = part[field] as unknown[];
    const middle = Math.ceil(items.length / 2);
    split({ ...part, [field]: items.slice(0, middle) });
    split({ ...part, [field]: items.slice(middle) });
  }
  split(packet);
  return parts.map((part, index) => annotate(part, index + 1, parts.length));
}
