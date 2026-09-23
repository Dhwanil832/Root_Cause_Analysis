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
}

export interface StageResponse<T> {
  output: T;
  durationMs: number;
  engine: string;
  validation: 'valid' | 'repaired';
  usage?: { inputTokens?: number; outputTokens?: number };
  attempts?: Array<{ attempt: number; raw: string; error?: string }>;
}

export interface ModelProvider {
  supports(model: ModelDescriptor): boolean;
  run<T>(request: StageRequest<T>): Promise<StageResponse<T>>;
}
