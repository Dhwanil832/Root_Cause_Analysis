import type { AgentId, ModelDescriptor } from '@/src/domain/types';
import type { z } from 'zod';

export interface ModelMedia {
  documentId: string;
  fileName: string;
  contentType: string;
  dataBase64: string;
  kind: 'image' | 'file';
}

export interface StageRequest<T> {
  stage: AgentId | 'story-answering';
  model: ModelDescriptor;
  systemPrompt: string;
  evidencePacket: unknown;
  schema: z.ZodType<T>;
  schemaName: string;
  media?: ModelMedia[];
  /** Application invariants that JSON Schema alone cannot express. */
  validateOutput?: (output: T) => string[];
  /** Optional legacy caller cap; ignored when noTruncation requests uncapped generation. */
  outputTokens?: number;
  contextWindow?: number;
  /** Explicit provider option, part of engine trace/cache identity. No fallback. */
  thinking?: boolean;
  sampling?: {temperature:number;top_p:number;top_k:number;min_p:number;presence_penalty:number;repeat_penalty:number;seed:number};
  noTruncation?: boolean;
  maxAttempts?: number;
  signal?: AbortSignal;
  /** Persist streamed text before parsing or applying the model response. */
  onChunk?: (text: string) => Promise<void>;
}

export interface StageResponse<T> {
  output: T;
  durationMs: number;
  engine: string;
  validation: 'valid' | 'repaired';
  usage?: { inputTokens?: number; outputTokens?: number; thinkingCharacters?:number };
  attempts?: Array<{ attempt: number; raw: string; error?: string; thinkingCharacters?:number;
    repetition?: {records:number;duplicateRecords:number;maxConsecutiveDuplicates:number} }>;
}

export interface ModelProvider {
  supports(model: ModelDescriptor): boolean;
  run<T>(request: StageRequest<T>): Promise<StageResponse<T>>;
}
