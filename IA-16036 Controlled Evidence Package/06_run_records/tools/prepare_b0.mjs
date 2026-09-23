import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
const pkg = fileURLToPath(new URL('../../', import.meta.url));
const original = path.resolve(pkg, '../Try 4');
const appPort = process.argv[2] || '3002';
if (!['3001', '3002', '3003'].includes(appPort)) throw Error('Use an isolated experiment port');
const promptVersion = (await fs.readFile(path.join(original, 'src/prompts/manifest.ts'), 'utf8')).match(/export const PROMPT_VERSION = '([^']+)'/)?.[1];
if (!promptVersion) throw Error('Cannot identify prompt version');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const seal = JSON.parse(await fs.readFile(path.join(pkg, 'package_seal.json')));
for (const [name, hash] of Object.entries(seal.hashes)) {
  if (sha(await fs.readFile(path.join(pkg, name))) !== hash) throw Error(`Package changed: ${name}`);
}
const dir = await fs.mkdtemp(path.join(pkg, '06_run_records/qwen-b0-'));
const app = path.join(dir, 'frozen-app');
await fs.mkdir(app);
for (const name of ['app','src','prompts','db','drizzle','public','package.json','package-lock.json','vite.config.ts','next.config.ts','tsconfig.json','next-env.d.ts','env.d.ts','.openai/hosting.json']) {
  await fs.cp(path.join(original,name), path.join(app,name), {recursive:true,errorOnExist:true,force:false});
}
await fs.symlink(path.join(original,'node_modules'), path.join(app,'node_modules'));
const codeHashes = {};
async function walk(folder) {
  for (const entry of await fs.readdir(folder,{withFileTypes:true})) {
    if (entry.isSymbolicLink()) continue;
    const full=path.join(folder,entry.name);
    if(entry.isDirectory()) await walk(full); else codeHashes[path.relative(app,full)]=sha(await fs.readFile(full));
  }
}
await walk(app);
const inventory=JSON.parse(await fs.readFile(path.join(pkg,'package_manifest.json')));
const records=inventory.records.filter(r=>r.release==='B0');
if(records.length!==7) throw Error('Unexpected B0 record count');
await fs.mkdir(path.join(dir,'input'));
await fs.mkdir(path.join(dir,'evaluator-frozen'));
const inputs=[];
for(const record of records){
  const bytes=await fs.readFile(path.join(pkg,record.path));
  const fileName=path.basename(record.path);
  await fs.writeFile(path.join(dir,'input',fileName),bytes,{flag:'wx'});
  inputs.push({...record,path:`input/${fileName}`,sha256:sha(bytes)});
}
for(const name of ['precise_review_targets.md','rubric.json','scoring_guide.md','run_protocol.md']) {
  await fs.copyFile(path.join(pkg,'05_evaluation',name),path.join(dir,'evaluator-frozen',name));
}
const manifest={
  caseId:'IA-16036',batch:'B0',targetVersion:1,createdAt:new Date().toISOString(),
  model:'ollama:qwen3.5:latest',expectedModelDigest:'6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7',
  originalApp:original,appDirectory:app,appUrl:`http://127.0.0.1:${appPort}`,proxyUrl:'http://127.0.0.1:11435',
  promptVersion,packageSealSha256:sha(await fs.readFile(path.join(pkg,'package_seal.json'))),
  generation:{temperature:0,think:false,contextLength:32768,outputBudgets:'Unchanged per-stage budgets in frozen src/providers/ollama.ts',providerAttempts:2,wholeCycleRetries:0},
  isolation:{freshLocalD1AndR2:true,noOriginalDatabaseCopied:true,noSecretsCopied:true,storyteller:false,externalAnswerJob:false,laterBatches:false,snapshotMatchesSource:true,sharedDependencySymlink:true},
  note:'In-cycle answer fetching may retrieve B0 documents; no external answer generation or new evidence is allowed. Existing provider permits one visible contract-repair attempt. Stop on failed stage or after V1.',
  inputs,codeHashes
};
await fs.writeFile(path.join(dir,'manifest.json'),JSON.stringify(manifest,null,2),{flag:'wx'});
console.log(JSON.stringify({directory:dir,app,records:inputs.length,codeFiles:Object.keys(codeHashes).length}));
