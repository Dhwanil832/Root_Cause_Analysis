import type {
  AgentId,
  AnalysisSnapshot,
  DocumentRecord,
  InvestigationAnswer,
  ModelDescriptor,
} from '@/src/domain/types';
import type { ModelMedia } from '@/src/providers/types';
import { enqueueRevision } from '@/src/server/engine-repository';
import { workerStep } from '@/src/engine/tasks/worker';

/** Application entry points: enqueue immutable inputs; execute one leased task.
 * Neither invokes the legacy whole-cycle orchestrator. */
export const queueInvestigation = enqueueRevision;
export const runInvestigationTask = workerStep;

export interface AnalysisRequest {
  incident: string;
  model: ModelDescriptor;
  answers?: InvestigationAnswer[];
  documents?: DocumentRecord[];
  previous?: AnalysisSnapshot;
  documentMedia?: ModelMedia[];
  strictExecution?: boolean;
  onCheckpoint?: (checkpoint: {
    stage: AgentId;
    status: 'completed' | 'failed' | 'blocked';
    payload: unknown;
  }) => Promise<void>;
}

/**
 * Compatibility type for archived tools only. Legacy synchronous invocation
 * is deliberately disabled; it cannot silently bypass the durable engine.
 */
export async function routeAnalysis(_request: AnalysisRequest): Promise<AnalysisSnapshot> {
  void _request;
  throw new Error('Try 6 uses durable input revisions and the investigation-led task worker. Submit through the incident/track repository; synchronous whole-investigation execution is disabled.');
}
