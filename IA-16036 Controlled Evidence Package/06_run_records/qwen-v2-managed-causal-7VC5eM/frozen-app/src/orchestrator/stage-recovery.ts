import { AsyncLocalStorage } from 'node:async_hooks';
import type { AgentId } from '@/src/domain/types';
import type { StageResponse } from '@/src/providers/types';

export interface RecoveryContext {
  cache: Map<string, StageResponse<unknown>>;
  persist: (stage: AgentId, payload: unknown) => Promise<void>;
  fingerprint: string;
}

const context = new AsyncLocalStorage<RecoveryContext>();

export async function fingerprint(value: unknown) {
  const bytes = new TextEncoder().encode(JSON.stringify(value));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, '0')).join('');
}

export function withStageRecovery<T>(recovery: RecoveryContext, work: () => Promise<T>) {
  return context.run(recovery, work);
}

/** Only validated provider output is reusable. Failed attempts remain separate. */
export async function recoverStage<T>(stage: AgentId, identity: unknown, work: () => Promise<StageResponse<T>>,
  validateSaved?: (output: unknown) => boolean) {
  const recovery = context.getStore();
  if (!recovery) return { ...await work(), reused: false };
  const key = await fingerprint([recovery.fingerprint, identity]);
  const saved = recovery.cache.get(key);
  if (saved && (!validateSaved || validateSaved(saved.output))) {
    await recovery.persist(stage, { kind: 'model-call-reused', key });
    return { ...saved as StageResponse<T>, reused: true };
  }
  if (saved) await recovery.persist(stage, { kind: 'model-call-cache-rejected', key,
    reason: 'Saved output no longer satisfies the current schema or output validator.' });
  try {
    const response = await work();
    // Await durable storage before the next model operation can begin.
    await recovery.persist(stage, { kind: 'model-call', key, requestIdentity: identity, response });
    recovery.cache.set(key, response);
    return { ...response, reused: false };
  } catch (error) {
    await recovery.persist(stage, { kind: 'model-call-failure', key, requestIdentity: identity,
      error: error instanceof Error ? error.message : String(error),
      attempts: (error as { attempts?: unknown })?.attempts });
    throw error;
  }
}
