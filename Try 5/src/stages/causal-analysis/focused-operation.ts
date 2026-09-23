import { z } from 'zod';
import type { ModelDescriptor } from '@/src/domain/types';
import { contextBudget, isContextOverflow } from '@/src/providers/context-budget';
import { runAgentStage } from '../run-agent-stage';
import type { ContextRecord } from './managed-operation';

type Decision = { decision: { summary: string; evidenceUsed: string[]; unknowns: string[]; alternatives: string[]; confidence: number } };
/** Split the TASK, never evidence pages whose verdicts would have to be ANDed.
 * Every review sees the selected evidence jointly. A single oversized task is
 * reported as such; it is never silently truncated or retried indefinitely. */
export async function runFocusedOperation<T, O extends Decision>(options: {
  model: ModelDescriptor; stage?: 'causal-analysis' | 'causal-verification'; schemaName: string;
  systemPrompt: string; targets: T[]; records: ContextRecord[];
  schemaFor: (targets: T[]) => z.ZodType<O>;
  packetFor: (targets: T[]) => Record<string, unknown>;
  validateOutput?: (output: O) => string[];
}): Promise<Array<Awaited<ReturnType<typeof runAgentStage<O>>>>> {
  const stage = options.stage || 'causal-analysis';
  const schema = options.schemaFor(options.targets);
  const packet = { ...options.packetFor(options.targets), retrievedEvidence: options.records };
  async function divide(): Promise<Array<Awaited<ReturnType<typeof runAgentStage<O>>>>> {
    if (options.targets.length < 2) throw new Error(`${options.schemaName}: complete evidence and one target exceed context; saved prior phases remain available.`);
    const middle = Math.ceil(options.targets.length / 2);
    return [...await runFocusedOperation({ ...options, targets: options.targets.slice(0, middle) }),
      ...await runFocusedOperation({ ...options, targets: options.targets.slice(middle) })];
  }
  if (!contextBudget(`${options.systemPrompt}\n\n`, packet, z.toJSONSchema(schema, { target: 'draft-7' }), stage).fits) return divide();
  try {
    return [await runAgentStage({ model: options.model, stage, schema, schemaName: options.schemaName,
      packet, systemPromptOverride: options.systemPrompt, validateOutput: options.validateOutput })];
  } catch (error) { if (isContextOverflow(error)) return divide(); throw error; }
}
