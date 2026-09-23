import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { DatabaseSync, backup } from 'node:sqlite';
import { fileURLToPath } from 'node:url';

const records = fileURLToPath(new URL('../', import.meta.url));
const parent = path.join(records, 'qwen-focused-story-v2-9Y8WDd');
const sourceApp = path.resolve(records, '../../Try 4');
const previous = JSON.parse(await fs.readFile(path.join(parent, 'manifest.json')));
const failure = JSON.parse(await fs.readFile(path.join(parent, 'v2-run-failure.json')));
if (!failure.error.includes('tagging: evidence packet has 60159 characters')) throw Error('Unexpected parent failure');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const changedFiles = [
  'src/knowledge/packet-limits.ts', 'src/stages/run-agent-stage.ts',
  'src/stages/causal-verification/packet-partitions.ts', 'src/story-agent/run.ts',
  'src/story-agent/contracts.ts', 'src/knowledge/document-extraction.ts',
  'src/prompts/manifest.ts', 'src/server/repository.ts',
];
const dir = await fs.mkdtemp(path.join(records, 'qwen-focused-v2-no-text-caps-'));
const app = path.join(dir, 'frozen-app');
const codeHashes = {};
for (const [name, hash] of Object.entries(previous.codeHashes)) {
  const original = await fs.readFile(path.join(previous.appDirectory, name));
  if (sha(original) !== hash) throw Error(`Parent source changed: ${name}`);
  const bytes = changedFiles.includes(name) ? await fs.readFile(path.join(sourceApp, name)) : original;
  await fs.mkdir(path.dirname(path.join(app, name)), { recursive: true });
  await fs.writeFile(path.join(app, name), bytes, { flag: 'wx' });
  codeHashes[name] = sha(bytes);
}
await fs.symlink(await fs.realpath(path.join(previous.appDirectory, 'node_modules')), path.join(app, 'node_modules'));
for (const name of ['input','input-b1','evaluator-frozen','frozen-rca-input.json','version-1.json','story-scenario.json',
  'questions-v1.json','story-result.json','story-after.json','candidate-answers.json','story-review.json',
  'expected-changes.md','story-citation-coverage-finding.md','frozen-v2-input.json']) {
  await fs.cp(path.join(parent, name), path.join(dir, name), { recursive: true, errorOnExist: true, force: false });
}
const sourceState = path.join(previous.appDirectory, '.wrangler/state');
const destinationState = path.join(app, '.wrangler/state');
await fs.cp(sourceState, destinationState, { recursive: true, filter: entry => !/\.sqlite(?:-wal|-shm)?$/.test(entry) });
const databaseSnapshots = [];
async function snapshot(folder) {
  for (const entry of await fs.readdir(folder, { withFileTypes: true })) {
    const full = path.join(folder, entry.name);
    if (entry.isDirectory()) await snapshot(full);
    else if (entry.name.endsWith('.sqlite')) {
      const target = path.join(destinationState, path.relative(sourceState, full));
      const db = new DatabaseSync(full, { readOnly: true });
      await backup(db, target); db.close();
      databaseSnapshots.push({ path: path.relative(app, target), sha256: sha(await fs.readFile(target)) });
    }
  }
}
await snapshot(sourceState);
const appUrl = 'http://127.0.0.1:3009';
const identity = JSON.parse(await fs.readFile(path.join(parent, 'identity.json')));
identity.url = `${appUrl}/incident/${identity.incidentId}`;
const manifest = { ...previous, createdAt: new Date().toISOString(), parentDirectory: parent,
  appDirectory: app, appUrl, codeHashes, changedFiles, databaseSnapshots,
  promptVersion: 'try4.3.4-no-hard-text-size-stops',
  harnessVariant: 'no-hard-text-size-stops-and-exact-story-resume',
  execution: 'Resume the saved V2 input once; do not regenerate storyteller answers or rerun matching validated upstream calls.',
  note: 'User requested removal of text-size stops. Removed RCA request rejection, story scenario/memory/response character ceilings, and extracted-text truncation. Lossless verification partitioning retains a soft target but never rejects an indivisible oversized record. Model, model context, prompts, semantic validators and answer/document payloads unchanged. Story resume now claims its ready round before applying saved answers so commit records the round correctly. Numeric model limits, API transport timeouts and non-size validity checks still apply.',
};
for (const [name, data] of Object.entries({ 'manifest.json': manifest, 'identity.json': identity })) {
  await fs.writeFile(path.join(dir, name), JSON.stringify(data, null, 2), { flag: 'wx' });
}
console.log(JSON.stringify({ directory: dir, app, appUrl, changedFiles }, null, 2));
