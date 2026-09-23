/** Read the text model's advertised context, never a vision encoder's window or
 * a RoPE original-training length. Metadata reads do not load model weights. */
export function ollamaContextWindow(info: Record<string, unknown> = {}): number | undefined {
  const architecture = info['general.architecture'];
  const direct = typeof architecture === 'string' ? info[`${architecture}.context_length`] : undefined;
  const candidates = Object.entries(info).filter(([key]) => /^[^.]+\.context_length$/.test(key)
    && !/vision|clip|projector/i.test(key));
  const value = direct ?? (candidates.length === 1 ? candidates[0][1] : undefined);
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0 ? value : undefined;
}

interface Metadata { capabilities: string[]; contextWindow?: number }
const metadataCache = new Map<string, Metadata>();
export async function readOllamaMetadata(name: string, digest?: string, signal?: AbortSignal): Promise<Metadata> {
  const base = (process.env.OLLAMA_BASE_URL || 'http://127.0.0.1:11434').replace(/\/$/, '');
  const key = digest ? `${base}:${digest}` : undefined;
  if (key && metadataCache.has(key)) return metadataCache.get(key)!;
  const response = await fetch(`${base}/api/show`, { method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ model: name }), signal });
  if (!response.ok) throw new Error(`Ollama model metadata returned ${response.status}.`);
  const payload = await response.json() as { capabilities?: string[]; model_info?: Record<string, unknown> };
  const metadata = { capabilities: payload.capabilities || [], contextWindow: ollamaContextWindow(payload.model_info) };
  if (key && metadata.contextWindow) metadataCache.set(key, metadata);
  return metadata;
}
