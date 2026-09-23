import { taggingSchema } from '@/src/domain/schemas';
import type { ModelDescriptor, StructuredIncident, TagResult } from '@/src/domain/types';
import { TAG_LABELS } from '@/src/domain/tag-catalog';
import { runAgentStage } from '../run-agent-stage';

export async function runTagging(model: ModelDescriptor, packet: unknown, structuredIncident: StructuredIncident) {
  const result = await runAgentStage({ stage: 'tagging', model, schema: taggingSchema, schemaName: 'incident_tags', packet: { packet, structuredIncident, fixedTaxonomy: TAG_LABELS } });
  const tags: TagResult[] = result.output.tags.map((tag) => ({ ...tag, label: TAG_LABELS[tag.id] }));
  return { ...result, tags };
}
