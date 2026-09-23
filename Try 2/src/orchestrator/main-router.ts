import type { AnalysisSnapshot, InvestigationAnswer, ModelDescriptor } from '@/src/domain/types';
import { runDeterministicAnalysis } from './deterministic-engine';

export interface AnalysisRequest {
  incident: string;
  model: ModelDescriptor;
  answers?: InvestigationAnswer[];
}

export interface AnalysisAdapter {
  supports(model: ModelDescriptor): boolean;
  analyze(request: AnalysisRequest): Promise<AnalysisSnapshot>;
}

const previewAdapter: AnalysisAdapter = {
  supports: () => true,
  async analyze(request) {
    return runDeterministicAnalysis(request.incident, request.answers);
  },
};

/**
 * Deterministic routing boundary. Provider adapters can be added without changing
 * persistence, the investigation state machine, or the dashboard contract.
 * The current build intentionally falls back to an inspectable deterministic
 * engine until a configured Ollama/API adapter returns validated structured output.
 */
export async function routeAnalysis(request: AnalysisRequest) {
  return previewAdapter.analyze(request);
}
