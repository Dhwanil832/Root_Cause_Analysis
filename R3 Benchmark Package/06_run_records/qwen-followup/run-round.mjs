import fs from 'node:fs/promises';
import { spawn } from 'node:child_process';
import path from 'node:path';
const dir = path.dirname(new URL(import.meta.url).pathname.replaceAll('%20', ' '));
const target = Number(process.argv[2]);
const base = 'http://localhost:3000';
const incidentId = '9276eeb0-a723-47ad-aca9-2be80c5b9b2e';
const trackId = 'b339a5c5-49b2-47a8-9122-d82948720dc5';
async function curl(args) {
  const p = spawn('/usr/bin/curl', ['-sS', ...args]);
  let out = '', err = '';
  p.stdout.on('data', x => out += x); p.stderr.on('data', x => err += x);
  const code = await new Promise(r => p.on('close', r));
  if (code) throw new Error(`curl ${code}: ${err}`);
  return JSON.parse(out);
}
async function snapshot() {
  return await curl(['--max-time','30', `${base}/api/incidents/${incidentId}`]);
}
const before = await snapshot();
const latest = before.incident.tracks.find(t=>t.id===trackId).versions.at(-1);
if(latest.number !== target-1) throw new Error(`Expected V${target-1}, found V${latest.number}`);
await fs.writeFile(path.join(dir, `version-${latest.number}.json`), JSON.stringify(latest,null,2));
const payload = path.join(dir, `answer-v${target}.json`);
await fs.access(payload);
const started = Date.now();
console.log(`Submitting answer for V${target}`);
const timer = setInterval(()=>console.log(`V${target}: ${Math.round((Date.now()-started)/1000)} seconds`),30000);
try {
  const result = await curl(['--max-time','14400','-H','Content-Type: application/json','--data-binary',`@${payload}`,`${base}/api/tracks/${trackId}/versions`]);
  await fs.writeFile(path.join(dir, `response-v${target}.json`), JSON.stringify(result,null,2));
  if(result.error) throw new Error(result.error);
  const after = await snapshot();
  const version = after.incident.tracks.find(t=>t.id===trackId).versions.at(-1);
  await fs.writeFile(path.join(dir,`version-${version.number}.json`), JSON.stringify(version,null,2));
  console.log(JSON.stringify({version:version.number,status:version.analysis.status,nodes:version.analysis.causalBoard.nodes.length,edges:version.analysis.causalBoard.edges.length,errors:version.analysis.stageErrors,questions:version.analysis.questions.map(q=>({id:q.id,text:q.text,status:q.status}))}));
} finally {clearInterval(timer);}
