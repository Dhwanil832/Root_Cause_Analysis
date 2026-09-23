import type { AnalysisSnapshot } from '../domain/types';

/** Execution completeness, not a claim that the RCA conclusions are correct. */
export function causalCommitProblems(analysis: AnalysisSnapshot) {
  const problems = (analysis.stageErrors || []).map(error => `${error.stage}: ${error.message}`);
  const causal = analysis.trace.find(entry => entry.stage === 'causal-analysis' && !['failed', 'fallback'].includes(entry.validation));
  if (!causal || causal.engine === 'harness' || causal.engine.startsWith('deterministic:')) {
    problems.push('No successful model-produced causal-analysis stage.');
  }
  const board = analysis.causalBoard;
  if (!board.nodes.length || !board.nodes.some(node => node.id === board.focalNodeId)) problems.push('Missing focal node.');
  if (!analysis.trace.some(entry => entry.stage === 'causal-verification' && !['failed', 'fallback'].includes(entry.validation))) {
    problems.push('Causal verification did not complete.');
  }
  return problems;
}
