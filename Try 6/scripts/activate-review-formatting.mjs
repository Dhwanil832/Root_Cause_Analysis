// Operator-only activation for an explicitly selected unpublished run. Wait for
// a task boundary, ask the app to pause atomically, then revalidate saved outputs.
// No provider call, cancellation, evidence edit, or completed-task resampling.
// SQLite is READ ONLY here: writes must use D1 inside the app to avoid SQLITE_BUSY.
import fs from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { setTimeout } from 'node:timers/promises';
import { readState } from '../src/engine/tasks/artifacts.ts';
import { digest } from '../src/engine/identity.ts';

const [runId,...taskIds]=process.argv.slice(2);
if(!runId)throw Error('Usage: node --import ./scripts/register-test-loader.mjs scripts/activate-review-formatting.mjs RUN_ID [FAILED_REVIEW_TASK_ID ...]');
const folder=path.resolve('.wrangler/state/v3/d1/miniflare-D1DatabaseObject'),matches=[];
for(const name of fs.readdirSync(folder).filter(n=>n.endsWith('.sqlite'))) {
  const candidate=new DatabaseSync(path.join(folder,name),{readOnly:true});
  try {
    if(candidate.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='engine_runs'").get()
      &&candidate.prepare('SELECT id FROM engine_runs WHERE id=?').get(runId))matches.push(path.join(folder,name));
  } finally {candidate.close();}
}
if(matches.length!==1)throw Error('Run not found in exactly one local database.');
const sqlite=new DatabaseSync(matches[0],{readOnly:true});
const db={prepare(sql){let args=[];return {
  bind(...values){args=values;return this;},
  async first(){return sqlite.prepare(sql).get(...args)||null;},
  async all(){return {results:sqlite.prepare(sql).all(...args)};},
};}};
import './legacy-disabled.mjs';
const base=process.env.RCA_APP_URL||'http://127.0.0.1:3015';
try {
  console.log('Waiting for a completed task boundary; current inference will not be cancelled.');
  while(true) {
    const row=sqlite.prepare('SELECT * FROM engine_runs WHERE id=?').get(runId);
    if(!row||!['running','queued'].includes(row.status))throw Error('Expected an active unpublished run; inspect its current state.');
    if(row.lease_until===0) {
      const state=await readState(db,row.state_json);
      if(state?.reviewFormattingPolicy)throw Error('Formatting policy already set; nothing to activate.');
      if(state&&!state.tasks.some(t=>t.status==='running')) {
        const response=await fetch(`${base}/api/tracks/${row.track_id}/review-formatting`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({runId,generation:row.generation,
          checkpointHash:await digest([row.input_json,row.state_json,row.snapshot_json]),recoverTaskIds:taskIds,
          reason:'User explicitly approved activation for the remainder of current V1; recover recognized no-premise formatting only.'})});
        const result=await response.json();
        if(response.ok){console.log(JSON.stringify(result,null,2));break;}
        if(!result.retryAtTaskBoundary)throw Error(result.error||`Activation returned ${response.status}`);
      }
    }
    await setTimeout(25);
  }
} finally {sqlite.close();}
