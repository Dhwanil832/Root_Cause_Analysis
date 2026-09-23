import { structuringSchema, type UnderstandingOutput } from '@/src/domain/schemas';
import { stableId } from '@/src/domain/ids';
import type { ModelDescriptor, StructuredIncident } from '@/src/domain/types';
import { runAgentStage } from '../run-agent-stage';

export async function runIncidentStructuring(model: ModelDescriptor, packet: unknown, understanding: UnderstandingOutput) {
  const result = await runAgentStage({ stage: 'incident-structuring', model, schema: structuringSchema, schemaName: 'incident_structuring', packet: { packet, understanding } });
  const structured: StructuredIncident = {
    summary: understanding.summary,
    focalEvent: understanding.focalEvent,
    actualImpact: understanding.actualImpact,
    potentialImpact: understanding.potentialImpact,
    normalState: understanding.normalState,
    eventState: understanding.eventState,
    entities: result.output.entities.map((entity) => ({ ...entity, id: stableId('entity', `${entity.type}:${entity.name}`) })),
    timeline: result.output.timeline.map((event) => ({ ...event, id: stableId('event', `${event.sequence}:${event.description}`) })),
    conditions: result.output.conditions,
    unknowns: [...new Set([...understanding.unknowns, ...result.output.unknowns])],
  };
  return { ...result, structured };
}
