/** SHA-256 identities for content/cache keys. Persistent record IDs are UUIDs. */
export async function digest(value: unknown) {
  const text = typeof value === 'string' ? value : JSON.stringify(value);
  const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(bytes), n => n.toString(16).padStart(2, '0')).join('');
}
export function normalize(text: string) { return text.toLowerCase().replace(/\s+/g, ' ').trim(); }
export function words(text: string) {
  const stop = new Set(['the','and','for','are','was','has','had','not','but','its','can','all','any','what','which','would','could','should','that','this','were','with','from','have','about','there','their','does','into','when','where','before','after']);
  return [...new Set(normalize(text).match(/[\p{L}\p{N}][\p{L}\p{N}_-]{1,}/gu) || [])].filter(w => !stop.has(w));
}
export function overlap(left: string, right: string) {
  const a = new Set(words(left)); return words(right).reduce((n, w) => n + Number(a.has(w)), 0);
}
