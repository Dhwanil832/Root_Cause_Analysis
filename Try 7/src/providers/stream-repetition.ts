/** A generation-progress policy, not an output-size or question-count limit. */
export const STREAM_REPETITION_POLICY = 'json-array-observation-v2';

export class StreamRepetitionError extends Error {
  readonly code = 'STREAM_REPETITION';
  readonly recordNumber: number;
  readonly repeatedRecords: number;
  readonly characterOffset: number;
  constructor(recordNumber: number, repeatedRecords: number, characterOffset: number) {
    super(`Ollama stream repetition: ${repeatedRecords} consecutive already-seen records by record ${recordNumber}; no new record content. Partial output preserved, not applied.`);
    this.name = 'StreamRepetitionError';
    this.recordNumber = recordNumber;
    this.repeatedRecords = repeatedRecords;
    this.characterOffset = characterOffset;
  }
}

type Frame = { kind: 'object' | 'array'; seen?: Set<string>; repeated: number; records: number };

// Key order is immaterial. Keep ALL values, including case, qualifiers, times,
// locations, citations and array order: similar but distinct facts must survive.
function signature(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(signature).join(',')}]`;
  if (value !== null && typeof value === 'object') return `{${Object.entries(value)
    .sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)
    .map(([key, item]) => `${JSON.stringify(key)}:${signature(item)}`).join(',')}}`;
  return JSON.stringify(value);
}

/** Incremental JSON lexical scanner. Only complete object records in root-level
 * arrays count; repeated words/quotes, nested citations and partial records do not.
 * A new record resets the streak. A repeated cycle A,B,A,B,A is caught too.
 * Repetition is telemetry, never a generation stop. This scanner never repairs,
 * deduplicates, or admits incomplete model output. */
export class StreamRepetitionGuard {
  readonly stats = { records: 0, duplicateRecords: 0, maxConsecutiveDuplicates: 0 };
  private frames: Frame[] = [];
  private inString = false;
  private escaped = false;
  private record: string | null = null;
  private recordDepth = 0;
  private offset = 0;

  push(text: string): void {
    for (const char of text) {
      this.offset += char.length;
      if (this.record !== null) this.record += char;
      if (this.inString) {
        if (this.escaped) this.escaped = false;
        else if (char === '\\') this.escaped = true;
        else if (char === '"') this.inString = false;
        continue;
      }
      if (char === '"') { this.inString = true; continue; }
      if (char === '{' || char === '[') {
        const parent = this.frames.at(-1);
        if (char === '{' && parent?.seen) {
          this.record = '{';
          this.recordDepth = this.frames.length + 1;
        }
        const collection = char === '[' && (this.frames.length === 0 || (this.frames.length === 1 && parent?.kind === 'object'));
        this.frames.push({ kind: char === '{' ? 'object' : 'array', seen: collection ? new Set() : undefined, repeated: 0, records: 0 });
      } else if (char === '}' || char === ']') {
        const closingRecord = char === '}' && this.record !== null && this.frames.length === this.recordDepth;
        this.frames.pop();
        if (closingRecord) {
          const raw = this.record!;
          this.record = null;
          const collection = this.frames.at(-1);
          if (!collection?.seen) continue;
          let key: string;
          try { key = signature(JSON.parse(raw)); }
          catch { continue; } // The normal output validator owns malformed JSON.
          collection.records++;
          collection.repeated = collection.seen.has(key) ? collection.repeated + 1 : 0;
          this.stats.records++;
          if(collection.repeated) this.stats.duplicateRecords++;
          this.stats.maxConsecutiveDuplicates=Math.max(this.stats.maxConsecutiveDuplicates,collection.repeated);
          collection.seen.add(key);
        }
      }
    }
  }
}
