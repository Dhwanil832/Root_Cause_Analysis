import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
const [pilot]=process.argv.slice(2);
if(!pilot)throw Error('Usage: verify-pilot-checkpoint.mjs PILOT_DIRECTORY');
const manifest=JSON.parse(fs.readFileSync(path.join(pilot,'manifest.json'),'utf8'));
const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const folder=path.resolve('.wrangler/state/v3/d1/miniflare-D1DatabaseObject');
const found=[];
for(const name of fs.readdirSync(folder).filter(n=>n.endsWith('.sqlite'))){
  const db=new DatabaseSync(path.join(folder,name),{readOnly:true});
  try{
    if(!db.prepare("SELECT name FROM sqlite_master WHERE name='engine_runs'").get())continue;
    const run=db.prepare('SELECT * FROM engine_runs WHERE id=?').get(manifest.runId);if(!run)continue;
    const json=encoded=>{const value=JSON.parse(encoded);return value?.$artifact?JSON.parse(db.prepare('SELECT content FROM engine_artifact_chunks WHERE artifact_id=? ORDER BY ordinal').all(value.$artifact).map(r=>r.content).join('')):value;};
    const encoded=json(run.state_json), state=encoded?.$engineState?Object.fromEntries(Object.entries(encoded.fields).map(([k,v])=>[k,json(v)])):encoded;
    const actual={generation:run.generation,inputHash:hash(json(run.input_json)),stateHash:hash(state),snapshotHash:hash(run.snapshot_json)};
    const unchanged=Object.entries(actual).every(([k,v])=>manifest[k]===v)&&run.status==='paused';
    found.push({runId:run.id,status:run.status,...actual,unchanged});
  }finally{db.close();}
}
console.log(JSON.stringify(found,null,2));
if(found.length!==1||!found[0].unchanged)process.exitCode=1;
