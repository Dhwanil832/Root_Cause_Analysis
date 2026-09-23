import type { AgentId, ModelDescriptor, TagId, TraceEntry } from '@/src/domain/types';
import { PROMPT_VERSION, promptFor } from '@/src/prompts/manifest';
import { runProviderStage } from '@/src/providers';
import type { z } from 'zod';
import type { ModelMedia } from '@/src/providers/types';
import { recoverStage, fingerprint } from '@/src/orchestrator/stage-recovery';
import { z as schemaTools } from 'zod';

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
  validateOutput?: (output: T) => string[];
  instruction?: string;
}) {
  const systemPrompt = `${promptFor(options.stage, options.specialist)}\n\n${options.instruction || ''}`;
  const schema = schemaTools.toJSONSchema(options.schema, { target: 'draft-7' });
  const result = await recoverStage(options.stage, {
    stage: options.stage, systemPrompt, schema, packet: options.packet, media: options.media,
  }, () => runProviderStage({
    stage: options.stage,
    model: options.model,
    systemPrompt,
    evidencePacket: options.packet,
    schema: options.schema,
    schemaName: options.schemaName,
    media: options.media,
    validateOutput: options.validateOutput,
  }), saved => {
    const parsed = options.schema.safeParse(saved);
    return parsed.success && !(options.validateOutput?.(parsed.data).length);
  });
  const decision = result.output.decision;
  const trace: TraceEntry = {
    id: await fingerprint([options.stage, options.packet, result.output]),
    stage: options.stage,
    summary: decision.summary,
    evidence: decision.evidenceUsed,
    unknowns: decision.unknowns,
    alternatives: decision.alternatives,
    confidence: decision.confidence,
    promptVersion: PROMPT_VERSION,
    engine: result.engine,
    durationMs: result.reused ? 0 : result.durationMs,
    validation: result.validation,
    reused: result.reused,
  };
  return { output: result.output, trace, providerAttempts: result.attempts };
}
