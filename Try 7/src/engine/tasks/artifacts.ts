import { digest } from '../identity';
import type { EngineState } from '../types';

// Small UTF-16 slices are <=48 KB even with multibyte text, far below D1's
// 2 MB row/string limit. Immutable content is written BEFORE publishing a pointer.
const CHUNK_CHARS = 12_000;
export function textChunks(text:string) {
  const chunks:string[]=[];
  for(let start=0;start<text.length;) {
    let end=Math.min(text.length,start+CHUNK_CHARS);
    const last=text.charCodeAt(end-1);
    if(end<text.length&&last>=0xD800&&last<=0xDBFF)end--;
    chunks.push(text.slice(start,end));start=end;
  }
  return chunks;
}
export async function putJSON(db: D1Database, value: unknown): Promise<string> {
  const text = JSON.stringify(value);
  if (text.length < CHUNK_CHARS) return text;
  const id = `json-u2:${await digest(text)}`;
  const existing = await db.prepare('SELECT COUNT(*) AS n FROM engine_artifact_chunks WHERE artifact_id=?').bind(id).first<{n:number}>();
  const chunks=textChunks(text),count=chunks.length;
  if (existing?.n !== count) {
    const statements = Array.from({length:count}, (_,i) => db.prepare('INSERT OR IGNORE INTO engine_artifact_chunks (artifact_id,ordinal,content) VALUES (?,?,?)')
      .bind(id,i,chunks[i]));
    for (let i=0;i<statements.length;i+=40) await db.batch(statements.slice(i,i+40));
  }
  return JSON.stringify({$artifact:id, chunks:count});
}
export async function readJSON<T>(db: D1Database, encoded: string): Promise<T> {
  const value = JSON.parse(encoded);
  if (!value || typeof value !== 'object' || !('$artifact' in value)) return value as T;
  const rows = await db.prepare('SELECT ordinal,content FROM engine_artifact_chunks WHERE artifact_id=? ORDER BY ordinal')
    .bind(value.$artifact).all<{ordinal:number;content:string}>();
  if (rows.results.length !== value.chunks || rows.results.some((r,i)=>r.ordinal!==i)) throw new Error(`Incomplete artifact ${value.$artifact}; checkpoint not readable.`);
  return JSON.parse(rows.results.map(r=>r.content).join('')) as T;
}
// Collections are independent content-addressed artifacts. Unchanged sources,
// findings, etc. are reused instead of copying them into every task checkpoint.
export async function putState(db: D1Database, state: EngineState | null): Promise<string> {
  if (!state) return 'null';
  const fields: Record<string,string> = {};
  for (const [key,value] of Object.entries(state)) if(value!==undefined) fields[key] = await putJSON(db,value);
  return putJSON(db, {$engineState:2, fields});
}
export async function readState(db: D1Database, encoded: string | null): Promise<EngineState | null> {
  if (!encoded) return null;
  const value = await readJSON<EngineState | { $engineState: number; fields: Record<string,string> } | null>(db,encoded);
  if (!value || !('$engineState' in value)) return value;
  const entries = await Promise.all(Object.entries(value.fields).map(async ([key,raw])=>[key,await readJSON(db,raw)]));
  return Object.fromEntries(entries) as EngineState;
}
