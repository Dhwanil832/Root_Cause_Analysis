// Offline, read-only replay of saved provider streams. No model calls or DB writes.
import fs from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { StreamRepetitionGuard, STREAM_REPETITION_POLICY } from '../src/providers/stream-repetition.ts';

const runId=process.argv[2];
if(!runId)throw Error('Usage: node --experimental-strip-types scripts/replay-stream-guard.mjs RUN_ID');
const folder=path.resolve('.wrangler/state/v3/d1/miniflare-D1DatabaseObject');
const matches=[];
for(const name of fs.readdirSync(folder).filter(n=>n.endsWith('.sqlite'))) {
  const db=new DatabaseSync(path.join(folder,name),{readOnly:true});
  try {
    if(db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='engine_runs'").get()
      && db.prepare('SELECT id FROM engine_runs WHERE id=?').get(runId))matches.push(path.join(folder,name));
  }finally{db.close();}
}
if(matches.length!==1)throw Error('Could not uniquely locate run.');
const db=new DatabaseSync(matches[0],{readOnly:true});
try {
  const results=[];
  for(const call of db.prepare('SELECT id,task_id,status,error FROM engine_calls WHERE run_id=? ORDER BY created_at').all(runId)) {
    const raw=db.prepare('SELECT content FROM engine_artifact_chunks WHERE artifact_id=? ORDER BY ordinal').all(`stream:${call.id}`).map(c=>c.content).join('');
    const guard=new StreamRepetitionGuard();
    let detection=null;
    try {for(let i=0;i<raw.length;i+=137)guard.push(raw.slice(i,i+137));}
    catch(error){detection={reason:error.message,characterOffset:error.characterOffset,recordNumber:error.recordNumber,repeatedRecords:error.repeatedRecords};}
    results.push({...call,rawCharacters:raw.length,detection});
  }
  console.log(JSON.stringify({runId,policy:STREAM_REPETITION_POLICY,results},null,2));
}finally{db.close();}
