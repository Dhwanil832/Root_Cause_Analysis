import type { AgentId, ModelDescriptor, TagId, TraceEntry } from '@/src/domain/types';
import { PROMPT_VERSION, promptFor } from '@/src/prompts/manifest';
import { runProviderStage } from '@/src/providers';
import type { z } from 'zod';
import type { ModelMedia } from '@/src/providers/types';

interface DecisionOutput {
  decision: {
    summary: string;
    evidenceUsed: string[];
    unknowns: string[];
    alternatives: string[];
    confidence: number;
  };
}

export async function runAgentStage<T extends DecisionOutput>(options: {
  stage: AgentId;
  model: ModelDescriptor;
  schema: z.ZodType<T>;
  schemaName: string;
  packet: unknown;
  specialist?: TagId;
  media?: ModelMedia[];
}) {
  const result = await runProviderStage({
    stage: options.stage,
    model: options.model,
    systemPrompt: promptFor(options.stage, options.specialist),
    evidencePacket: options.packet,
    schema: options.schema,
    schemaName: options.schemaName,
    media: options.media,
  });
  const decision = result.output.decision;
  const trace: TraceEntry = {
    id: crypto.randomUUID(),
    stage: options.stage,
    summary: decision.summary,
    evidence: decision.evidenceUsed,
    unknowns: decision.unknowns,
    alternatives: decision.alternatives,
    confidence: decision.confidence,
    promptVersion: PROMPT_VERSION,
    engine: result.engine,
    durationMs: result.durationMs,
    validation: result.validation,
  };
  return { output: result.output, trace };
}
