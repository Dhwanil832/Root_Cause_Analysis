import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { DatabaseSync, backup } from 'node:sqlite';
import { fileURLToPath } from 'node:url';

// A new workflow experiment descended from the committed B0 board. No model
// calls, changed prompts, answer-key access, or writes to the parent experiment.
const records = fileURLToPath(new URL('../', import.meta.url));
const packageRoot = path.resolve(records, '..');
const focused = process.argv[2] === 'focused';
if (process.argv[2] && !focused) throw Error('Unknown experiment profile');
const parent = path.join(records, 'qwen-b0-verification-packets-hnHgwz');
const previous = JSON.parse(await fs.readFile(path.join(parent, 'manifest.json')));
const result = JSON.parse(await fs.readFile(path.join(parent, 'result.json')));
if (result.status !== 'completed_stopped_after_v1' || result.stageErrors.length) throw Error('A completed parent V1 is required');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const dir = await fs.mkdtemp(path.join(records, focused ? 'qwen-focused-story-v2-' : 'qwen-b1-story-cycle-'));
const app = path.join(dir, 'frozen-app');
for (const [name, hash] of Object.entries(previous.codeHashes)) {
  const bytes = await fs.readFile(path.join(previous.appDirectory, name));
  if (sha(bytes) !== hash) throw Error(`Parent source changed: ${name}`);
  await fs.mkdir(path.dirname(path.join(app, name)), { recursive: true });
  await fs.writeFile(path.join(app, name), bytes, { flag: 'wx' });
}
await fs.symlink(await fs.realpath(path.join(previous.appDirectory, 'node_modules')), path.join(app, 'node_modules'));
for (const name of ['input', 'evaluator-frozen', 'frozen-rca-input.json', 'version-1.json']) {
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
      await backup(db, target);
      db.close();
      databaseSnapshots.push({ path: path.relative(app, target), sha256: sha(await fs.readFile(target)) });
    }
  }
}
await snapshot(sourceState);
const inventory = JSON.parse(await fs.readFile(path.join(packageRoot, 'package_manifest.json')));
const newInputs = [];
await fs.mkdir(path.join(dir, 'input-b1'));
for (const record of inventory.records.filter(r => r.release === 'B1' && (!focused || ['IA-P01', 'IA-P02'].includes(r.id)))) {
  const bytes = await fs.readFile(path.join(packageRoot, record.path));
  const name = `input-b1/${path.basename(record.path)}`;
  await fs.writeFile(path.join(dir, name), bytes, { flag: 'wx' });
  newInputs.push({ id: record.id, release: 'B1', scope: record.scope, path: name, sha256: sha(bytes) });
}
if (newInputs.map(r => r.id).join(',') !== (focused ? 'IA-P01,IA-P02' : 'IA-P01,IA-P02,IA-P03,IA-C01')) throw Error('Unexpected evidence inventory');
const sources = [];
for (const record of [...previous.inputs, ...newInputs]) {
  const bytes = await fs.readFile(path.join(dir, record.path));
  if (sha(bytes) !== record.sha256) throw Error(`Changed evidence: ${record.id}`);
  const text = bytes.toString('utf8');
  sources.push({ id: record.id, title: text.split('\n').find(line => line.startsWith('# '))?.slice(2) || path.basename(record.path),
    sourceClass: 'Synthetic evaluation record; retain the provenance and limitations stated in the record.', text, available: true });
}
const scenario = {
  title: focused ? 'IA-16036 — focused instrument-record evidence holder' : 'IA-16036 — fixed-record evidence holder, first answer batch',
  hiddenTruth: 'This is a fixed synthetic evaluation, not an authentic plant investigation. Only the attached available source records may establish releasable facts. No additional private causal answer key is supplied. Missing records and undocumented events remain unknown or unavailable; do not invent them, promote absence of documentation to absence of an action, or resolve a disputed assertion without supporting evidence.',
  sources,
};
const appUrl = focused ? 'http://127.0.0.1:3008' : 'http://127.0.0.1:3007';
const identity = JSON.parse(await fs.readFile(path.join(parent, 'identity.json')));
identity.url = `${appUrl}/incident/${identity.incidentId}`;
const manifest = { ...previous, createdAt: new Date().toISOString(), batch: 'B1', baseVersion: 1, targetVersion: 2,
  appDirectory: app, appUrl, parentDirectory: parent, resumeProfile: undefined,
  execution: 'One separate story-answering job, frozen answer review, then one separately dispatched RCA job. Not a new B0 run or a four-version loop.',
  experimentType: focused ? 'focused_P01_P02_story_and_RCA; not the complete B1 release or a model-ranking trial' : 'story_answering_handoff; not directly comparable to a documents-only B1 pass',
  selectedQuestionIds: focused ? ['bq-1fanm2w', 'vq-52l0ma', 'vq-zyn2wt', 'vq-1cq95dh'] : undefined,
  inputs: [...previous.inputs, ...newInputs], databaseSnapshots, changedFiles: [],
  isolation: { ...previous.isolation, storyteller: true, externalAnswerJob: true, laterBatches: false },
  note: focused
    ? 'User-authorized focused experiment: four unmodified existing V1 questions, B0 plus IA-P01/IA-P02 only. Both new documents and the four unedited story responses enter V2 after review. No other B1 records, future batches, evaluator key, expected conclusions or earlier failed story responses are supplied. Question selection is not a global cap. Memory limits and reasoning prompts remain unchanged. Generate and apply are separate jobs; stop on failure.'
    : 'Only B0 and B1 source records enter the storyteller. All four B1 documents will enter V2. No B2/B3 records, evaluator key, grading targets, or invented answers enter either model. Generate and apply remain separate requests. Exact citation checks do not replace semantic review. Stop on failure; no automatic whole-job retries.',
  frozenV1Sha256: sha(await fs.readFile(path.join(dir, 'version-1.json'))),
  scenarioSha256: sha(JSON.stringify(scenario)),
};
for (const [name, data] of Object.entries({ 'manifest.json': manifest, 'identity.json': identity, 'story-scenario.json': scenario })) {
  await fs.writeFile(path.join(dir, name), JSON.stringify(data, null, 2), { flag: 'wx' });
}
console.log(JSON.stringify({ directory: dir, app, appUrl, sourceCount: sources.length, scenarioCharacters: JSON.stringify(scenario).length, changedFiles: [] }, null, 2));
