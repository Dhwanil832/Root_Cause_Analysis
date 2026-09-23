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
  onCheckpoint?: (checkpoint: {
    stage: AgentId;
    status: 'completed' | 'failed' | 'blocked';
    payload: unknown;
  }) => Promise<void>;
}

/**
 * Stable harness boundary used by every provider. A model receives the same staged
 * workflow and output contracts; invalid or unavailable stages fall back without
 * losing the investigation version.
 */
export async function routeAnalysis(request: AnalysisRequest) {
  return runInvestigationCycle(request);
}
