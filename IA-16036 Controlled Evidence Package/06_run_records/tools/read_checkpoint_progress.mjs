import fs from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';

// Read-only inspection of the actual run. No model calls, retries or writes.
const dir = path.resolve(process.argv[2]);
const folder = path.join(dir, 'frozen-app/.wrangler/state/v3/d1/miniflare-D1DatabaseObject');
const files = fs.readdirSync(folder).filter(name => name.endsWith('.sqlite') && name !== 'metadata.sqlite');
if (files.length !== 1) throw Error('Expected exactly one isolated application database');
const db = new DatabaseSync(path.join(folder, files[0]), { readOnly: true });
const rows = db.prepare('SELECT stage,status,created_at,payload_json FROM stage_checkpoints ORDER BY created_at,sequence').all();
const checkpoints = rows.map(row => ({ stage: row.stage, status: row.status, at: row.created_at, payload: JSON.parse(row.payload_json) }));
const stage = process.argv[3];
if (stage) {
  console.log(JSON.stringify(checkpoints.filter(row => row.stage === stage && row.payload.kind?.startsWith('model-call')), null, 2));
} else {
  const calls = checkpoints.filter(row => row.payload.kind === 'model-call');
  console.log(JSON.stringify({
    now: new Date().toISOString(),
    versions: db.prepare('SELECT COUNT(*) AS n FROM versions').get().n,
    successfulModelCalls: calls.length,
    modelDurationSeconds: Math.round(calls.reduce((sum, row) => sum + row.payload.response.durationMs, 0) / 1000),
    checkpoints: checkpoints.map(row => ({ stage: row.stage, status: row.status, at: row.at, kind: row.payload.kind, error: row.payload.error })),
  }, null, 2));
}
db.close();
