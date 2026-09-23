import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { DatabaseSync, backup } from 'node:sqlite';
import { fileURLToPath } from 'node:url';

// Snapshot the failed experiment, never edit it in place or import later data.
const records = fileURLToPath(new URL('../', import.meta.url));
const localRejections = process.argv[2] === 'local-rejections';
const verificationPackets = process.argv[2] === 'verification-packets';
if (process.argv[2] && !localRejections && !verificationPackets) throw Error('Unknown resume profile');
const parent = path.join(records, verificationPackets ? 'qwen-b0-local-rejections-etH9Rd' : localRejections ? 'qwen-b0-resume-jJlucQ' : 'qwen-b0-ClBDGA');
const original = path.resolve(records, '../../Try 4');
const previous = JSON.parse(await fs.readFile(path.join(parent, 'manifest.json')));
const failure = JSON.parse(await fs.readFile(path.join(parent, 'failure.json')));
if (!failure.error.includes(verificationPackets ? 'evidence packet has 64421 characters' : localRejections ? 'Self links are not causal explanations.' : 'Claim claim-1gqp40y') || previous.batch !== 'B0') throw Error('Unexpected parent experiment');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
for (const [name, hash] of Object.entries(previous.codeHashes)) {
  if (sha(await fs.readFile(path.join(previous.appDirectory, name))) !== hash) throw Error(`Parent source changed: ${name}`);
}
const dir = await fs.mkdtemp(path.join(records, verificationPackets ? 'qwen-b0-verification-packets-' : localRejections ? 'qwen-b0-local-rejections-' : 'qwen-b0-resume-'));
const app = path.join(dir, 'frozen-app');
await fs.mkdir(app);
for (const name of ['app','src','prompts','db','drizzle','public','package.json','package-lock.json','vite.config.ts','next.config.ts','tsconfig.json','next-env.d.ts','env.d.ts','.openai/hosting.json']) {
  await fs.cp(path.join(original, name), path.join(app, name), { recursive: true, errorOnExist: true, force: false });
}
await fs.symlink(path.join(original, 'node_modules'), path.join(app, 'node_modules'));
for (const name of ['input', 'evaluator-frozen', 'frozen-rca-input.json', 'identity.json']) {
  await fs.cp(path.join(parent, name), path.join(dir, name), { recursive: true, errorOnExist: true, force: false });
}
const sourceState = path.join(previous.appDirectory, '.wrangler/state');
const destinationState = path.join(app, '.wrangler/state');
await fs.cp(sourceState, destinationState, { recursive: true, filter: entry => !/\.sqlite(?:-wal|-shm)?$/.test(entry) });
const databaseSnapshots = [];
async function snapshotDatabases(folder) {
  for (const entry of await fs.readdir(folder, { withFileTypes: true })) {
    const full = path.join(folder, entry.name);
    if (entry.isDirectory()) await snapshotDatabases(full);
    else if (entry.name.endsWith('.sqlite')) {
      const target = path.join(destinationState, path.relative(sourceState, full));
      const db = new DatabaseSync(full, { readOnly: true });
      await backup(db, target);
      db.close();
      databaseSnapshots.push({ path: path.relative(app, target), sha256: sha(await fs.readFile(target)) });
    }
  }
}
await snapshotDatabases(sourceState);
const codeHashes = {};
async function hashCode(folder) {
  for (const entry of await fs.readdir(folder, { withFileTypes: true })) {
    if (entry.isSymbolicLink() || entry.name === '.wrangler') continue;
    const full = path.join(folder, entry.name);
    if (entry.isDirectory()) await hashCode(full);
    else codeHashes[path.relative(app, full)] = sha(await fs.readFile(full));
  }
}
await hashCode(app);
const changedFiles = Object.keys(codeHashes).filter(name => codeHashes[name] !== previous.codeHashes[name]);
const promptVersion = (await fs.readFile(path.join(app, 'src/prompts/manifest.ts'), 'utf8')).match(/export const PROMPT_VERSION = '([^']+)'/)?.[1];
const manifest = { ...previous, createdAt: new Date().toISOString(), promptVersion,
  parentDirectory: parent, appDirectory: app, appUrl: verificationPackets ? 'http://127.0.0.1:3006' : localRejections ? 'http://127.0.0.1:3005' : 'http://127.0.0.1:3004', proxyUrl: null,
  resumeProfile: verificationPackets ? 'verification-packets' : localRejections ? 'local-rejections' : 'claim-review',
  execution: 'Explicit resumed copy, not an independent fresh model evaluation',
  isolation: { ...previous.isolation, freshLocalD1AndR2: false, noOriginalDatabaseCopied: false,
    stateCopiedOnlyFromParentExperiment: true, originalExperimentUnchanged: true },
  note: verificationPackets
    ? 'Resume saved B0 once. Only oversized causal-verification context is partitioned, measuring the entire serialized packet. Every record and target is retained across review; one-page support never overrides a failed check elsewhere. Already fitting packets, prompts, schemas, model, evidence and causal generation are unchanged. Stop on failure or first committed V1. Full request identities and raw responses remain preserved.'
    : localRejections
    ? 'Resume saved B0 once with item-local semantic rejection. Prompts, schema, evidence, model, node/link batching and generation settings unchanged from parent. Successful matching calls are reused; the failed link call is regenerated, never imported as validated output. Rejected edges and reasons remain visible without poisoning endpoint facts. Stop on failure or first committed V1. Full stage request identities preserved; no wire-level capture.'
    : 'Resume saved B0 work once. Per-call prompt/schema/packet matches and current validators control reuse. Claim review reruns under a changed contract. Stop on failure or first committed V1. New calls preserve full stage request identity in checkpoints; no wire-level capture.',
  codeHashes, changedFiles, databaseSnapshots,
};
await fs.writeFile(path.join(dir, 'manifest.json'), JSON.stringify(manifest, null, 2), { flag: 'wx' });
console.log(JSON.stringify({ directory: dir, app, promptVersion, changedFiles, databaseSnapshots: databaseSnapshots.length }, null, 2));
