import { correctiveActionSchema } from '@/src/domain/schemas';
import { stableId } from '@/src/domain/ids';
import type { CorrectiveAction, ModelDescriptor } from '@/src/domain/types';
import { runAgentStage } from '../run-agent-stage';

export async function runCorrectiveActions(model: ModelDescriptor, packet: unknown, keyToId: Map<string, string>) {
  const result = await runAgentStage({ stage: 'corrective-actions', model, schema: correctiveActionSchema, schemaName: 'corrective_actions', packet });
  const actions: CorrectiveAction[] = result.output.actions.map((action) => ({
    id: stableId('action', action.title), title: action.title, description: action.description,
    type: action.type, causalTargetIds: action.causalTargetKeys.map((key) => keyToId.get(key) || key),
    ownerRole: action.ownerRole, completionEvidence: action.completionEvidence,
    effectivenessCheck: action.effectivenessCheck, status: 'proposed',
  }));
  return { ...result, actions };
}
