// Read-only local diagnostics. Never open the live D1 database for native writes.
import {readdirSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {fileURLToPath} from 'node:url';
const folder = new URL('../.wrangler/state/v3/d1/miniflare-D1DatabaseObject/', import.meta.url);
const files = readdirSync(folder).filter(n => n.endsWith('.sqlite'));
const matches = files.filter(name => {
  const db = new DatabaseSync(fileURLToPath(new URL(name, folder)), {readOnly: true});
  try {return !!db.prepare("SELECT name FROM sqlite_master WHERE name='engine_runs'").get()
    && !!db.prepare('SELECT id FROM engine_runs WHERE id=?').get(process.argv[2]);}
  finally {db.close();}
});
if (matches.length !== 1) throw Error('Expected exactly one local database containing the requested run.');
const sqlite = new DatabaseSync(fileURLToPath(new URL(matches[0], folder)), {readOnly: true});
function json(encoded) {
  const value = JSON.parse(encoded);
  if (value?.$artifact) return JSON.parse(sqlite.prepare('SELECT content FROM engine_artifact_chunks WHERE artifact_id=? ORDER BY ordinal').all(value.$artifact).map(r => r.content).join(''));
  return value;
}
try {
  const row = sqlite.prepare('SELECT * FROM engine_runs WHERE id=?').get(process.argv[2]);
  if (!row) throw Error('Usage: node scripts/inspect-run.mjs RUN_ID [--details]');
  const encoded = json(row.state_json);
  const state = encoded?.$engineState ? Object.fromEntries(Object.entries(encoded.fields).map(([k,v])=>[k,json(v)])) : encoded;
  const calls = sqlite.prepare('SELECT id,status,created_at,updated_at,error FROM engine_calls WHERE run_id=? ORDER BY created_at DESC LIMIT 2').all(row.id);
  for (const call of calls) {
    call.publicOutputChars = sqlite.prepare('SELECT COALESCE(SUM(length(content)),0) AS n FROM engine_artifact_chunks WHERE artifact_id=?').get(`stream:${call.id}`).n;
    if (process.argv.includes('--call-metrics')) {
      const encodedCall=sqlite.prepare('SELECT request_json,result_json FROM engine_calls WHERE id=?').get(call.id);
      const request=json(encodedCall.request_json),result=json(encodedCall.result_json);
      call.requestFieldChars=Object.fromEntries(Object.entries(request||{}).map(([k,v])=>[k,JSON.stringify(v).length]));
      call.packetFieldChars=Object.fromEntries(Object.entries(request?.packet||{}).map(([k,v])=>[k,JSON.stringify(v).length]));
      call.usage=result?.usage;
      call.attempts=result?.providerAttempts?.map(a=>({attempt:a.attempt,thinkingCharacters:a.thinkingCharacters,repetition:a.repetition,error:a.error}));
    }
    if (process.argv.includes('--call-output')) {
      const result=json(sqlite.prepare('SELECT result_json FROM engine_calls WHERE id=?').get(call.id).result_json);
      call.publicResult=result?.output?.output ?? result?.output ?? null;
    }
  }
  const count = field => state[field]?.length;
  const summary = {at: new Date().toISOString(),runId:row.id,status:row.status,version:row.number,generation:row.generation,
    workerLeaseUntil:row.lease_until ? new Date(row.lease_until).toISOString() : null,
    phase:state.phase,stage:state.investigation?.stage,ready:state.investigation?.ready,pauseReason:row.pause_reason,
    findings:count('findings'),questions:count('questions'),quarantine:count('quarantine'),
    nodes:state.propositions.filter(p=>state.investigation?.selectedFindingIds.includes(p.findingId)).length+1,
    relationships:state.relationships.filter(e=>e.proposedBy?.length).length,
    tasks:state.tasks.filter(t=>t.kind!=='read').map(({kind,owner,status,partial,error,traceId,durationMs})=>({kind,owner,status,partial,error,traceId,durationMs})),calls};
  if (process.argv.includes('--details')) Object.assign(summary,{position:state.investigation,propositions:state.propositions,
    relationships:state.relationships,questionDetails:state.questions,quarantined:state.quarantine});
  if (process.argv.includes('--review-plan')) {
    const active = new Set([...state.propositions.filter(p=>state.investigation?.selectedFindingIds.includes(p.findingId)).map(p=>p.findingId),
      ...state.relationships.filter(e=>e.proposedBy?.length).flatMap(e=>e.findingIds)]);
    summary.reviewPlan=state.tasks.filter(t=>t.kind==='review').map(t=>({id:t.id,status:t.status,
      statement:state.findings.find(f=>f.id===t.targetIds[0])?.statement,usedByCurrentBoard:active.has(t.targetIds[0])}));
  }
  if (process.argv.includes('--brief')) summary.tasks = state.tasks.reduce((counts,t)=>{
    const key=`${t.kind}:${t.status}`;counts[key]=(counts[key]||0)+1;return counts;
  },{});
  console.log(JSON.stringify(summary,null,2));
} finally {sqlite.close();}
