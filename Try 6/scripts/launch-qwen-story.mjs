import './legacy-disabled.mjs';
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const app=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const dir=await fs.mkdtemp(path.resolve(app,'../R3 Benchmark Package/06_run_records/qwen-story-autonomous-'));
async function live(url){try{const r=await fetch(url,{signal:AbortSignal.timeout(8000)});return r.ok;}catch{return false;}}
async function launch(command,args,file){
  const log=await fs.open(path.join(dir,file),'a');
  const child=spawn(command,args,{cwd:app,detached:true,stdio:['ignore',log.fd,log.fd]});
  await new Promise((resolve,reject)=>{child.once('spawn',resolve);child.once('error',reject);});
  child.unref();await log.close();return child.pid;
}
const services={};
if(!await live('http://127.0.0.1:11434/api/tags'))services.ollamaPid=await launch('/opt/homebrew/bin/ollama',['serve'],'ollama.log');
if(!await live('http://localhost:3000/api/incidents'))services.appPid=await launch(process.execPath,[path.join(app,'node_modules/.bin/vinext'),'dev'],'app.log');
for(let i=0;i<30;i++){
  if(await live('http://localhost:3000/api/incidents')&&await live('http://127.0.0.1:11434/api/tags'))break;
  if(i===29)throw Error(`Services did not become ready. Inspect ${dir}`);
  await new Promise(resolve=>setTimeout(resolve,1000));
}
// caffeinate keeps this specific unattended job alive through idle sleep. It
// exits with the runner; it cannot keep a powered-off or closed laptop running.
const pid=await launch('/usr/bin/caffeinate',['-i','-s',process.execPath,'--experimental-strip-types',path.join(app,'scripts/autonomous-qwen-story.mjs'),'--run-dir',dir],'runner.log');
const launchInfo={runDir:dir,pid,services,startedAt:new Date().toISOString(),targetVersions:4};
await fs.writeFile(path.join(dir,'launch.json'),JSON.stringify(launchInfo,null,2));
console.log(JSON.stringify(launchInfo));
