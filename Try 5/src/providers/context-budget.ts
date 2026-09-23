import { evidenceMessage } from './json';

/** Planning estimate, NOT a tokenizer. Ollama's truncate:false is the authoritative
 * admission check. Include the schema even though this backend uses it as grammar. */
export function contextBudget(systemPrompt: string, packet: unknown, schema: unknown,
  stage: string, repair = '') {
  const contextTokens = Number(process.env.OLLAMA_CONTEXT_LENGTH || 32_768);
  const outputTokens = stage === 'causal-verification' ? 4_000 : 6_400;
  const inputBytes = new TextEncoder().encode(systemPrompt + evidenceMessage(packet, repair) + JSON.stringify(schema)).length;
  const estimatedInputTokens = Math.ceil(inputBytes / 2);
  const reserveTokens = 2_048; // template, special tokens, and repair headroom
  return { contextTokens, outputTokens, inputBytes, estimatedInputTokens, reserveTokens,
    fits: estimatedInputTokens + outputTokens + reserveTokens <= contextTokens,
    estimateMethod: 'UTF-8 bytes / 2; planning only, server enforces no truncation' };
}

export class ContextOverflowError extends Error {
  constructor(message: string) { super(message); this.name = 'ContextOverflowError'; }
}

export function isContextOverflow(error: unknown) {
  return error instanceof ContextOverflowError;
}
