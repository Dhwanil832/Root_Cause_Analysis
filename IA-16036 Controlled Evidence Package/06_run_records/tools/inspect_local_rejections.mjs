import fs from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';

// Inspect persisted outputs of the real resumed experiment. No model calls,
// writes, fixtures, acceptance overrides or automatic retries.
const directory = path.resolve(process.argv[2]);
const manifest = JSON.parse(fs.readFileSync(path.join(directory, 'manifest.json'), 'utf8'));
const folder = path.join(manifest.appDirectory, '.wrangler/state/v3/d1/miniflare-D1DatabaseObject');
const databases = fs.readdirSync(folder).filter(n => n.endsWith('.sqlite') && n !== 'metadata.sqlite');
if (databases.length !== 1) throw Error('Expected one isolated RCA database');
const db = new DatabaseSync(path.join(folder, databases[0]), { readOnly: true });
const rows = db.prepare('SELECT stage,status,created_at,payload_json FROM stage_checkpoints ORDER BY created_at,sequence').all()
  .map(row => ({ stage: row.stage, status: row.status, at: row.created_at, payload: JSON.parse(row.payload_json) }));
const fresh = rows.filter(row => row.at >= manifest.createdAt);
const analysis = fresh.findLast(row => row.stage === 'causal-analysis' && row.status === 'completed' && row.payload.board);
const verified = fresh.findLast(row => row.stage === 'causal-verification' && row.status === 'completed' && row.payload.board);
const board = analysis?.payload.board;
const retainedIds = new Set([...(board?.nodes || []), ...(board?.edges || [])].map(x => x.id));
const rejected = board?.rejectedEdges || [];
const result = {
  at: new Date().toISOString(),
  versions: db.prepare('SELECT COUNT(*) AS n FROM versions').get().n,
  reusedCalls: fresh.filter(row => row.payload.kind === 'model-call-reused').length,
  newCalls: fresh.filter(row => row.payload.kind === 'model-call').length,
  failures: fresh.filter(row => row.status === 'failed').map(row => ({ stage: row.stage, error: row.payload.error })),
  latest: fresh.slice(-2).map(row => ({ stage: row.stage, kind: row.payload.kind, at: row.at })),
  causalBoard: board ? {
    savedAt: analysis.at, nodes: board.nodes.length, activeEdges: board.edges.length,
    rejectedProposals: rejected.length, maturity: board.maturity,
    rawEdges: analysis.payload.rawModelOutput.edges.length,
    allRawEdgesAccountedFor: analysis.payload.rawModelOutput.edges.length === board.edges.length + rejected.length,
    activeSelfLinks: board.edges.filter(edge => edge.from === edge.to).length,
    causalEdgesWithoutTests: board.edges.filter(edge => ['caused', 'enabled', 'failed-to-prevent'].includes(edge.type)
      && (!edge.counterfactual.trim() || !edge.competingExplanation.trim())).length,
    rejectionFindingsMisassignedToRetainedTargets: board.verificationFindings.filter(f => retainedIds.has(f.targetId)).length,
    everyRejectionOwnsFinding: rejected.every(edge => board.verificationFindings.some(f => f.targetId === edge.id)),
    rejections: rejected.map(edge => ({ id: edge.id, from: edge.fromLabel, to: edge.toLabel, reasons: edge.reasons })),
  } : null,
  verification: verified ? {
    savedAt: verified.at, maturity: verified.payload.board.maturity,
    reviewedNodes: verified.payload.board.nodes.filter(n => n.verified).length,
    reviewedEdges: verified.payload.board.edges.filter(e => e.verified).length,
    findings: verified.payload.board.verificationFindings.length,
    preservedRejections: verified.payload.board.rejectedEdges?.length || 0,
  } : null,
};
db.close();
console.log(JSON.stringify(result, null, 2));
