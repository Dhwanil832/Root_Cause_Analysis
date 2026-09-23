import type {
  AgentId,
  AnalysisSnapshot,
  DocumentRecord,
  InvestigationAnswer,
  ModelDescriptor,
} from '@/src/domain/types';
import { runInvestigationCycle } from './investigation-loop';
import type { ModelMedia } from '@/src/providers/types';

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
 * Stable harness boundary used by every provider. A model receives the same staged
 * workflow and output contracts. Strict experiments stop on unrecovered stage
 * failures; ordinary UI runs may preserve an explicitly incomplete snapshot.
 */
export async function routeAnalysis(request: AnalysisRequest) {
  return runInvestigationCycle(request);
}
