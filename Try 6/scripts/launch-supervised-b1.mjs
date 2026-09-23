// Operator-side launch adapter. Uses the app's repository and local D1/R2,
// without changing prompts, the engine, or existing investigation inputs.
// Scheduled B1 records are attached atomically before a single initial revision;
// they are not fabricated answers to questions the model has not asked.
import './legacy-disabled.mjs';
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
import { registerHooks } from 'node:module';
import { execFileSync } from 'node:child_process';
import { getPlatformProxy } from 'wrangler';
import './register-test-loader.mjs';

const root = path.resolve(import.meta.dirname, '..');
if (process.cwd() !== root) throw Error('Run this adapter from Try 5.');
const contentOnly=process.argv.includes('--case-content-only');
if(process.argv.slice(2).some(arg=>arg!=='--case-content-only'))throw Error('Unknown launch option.');
const packageDir = path.resolve('../IA-16036 Controlled Evidence Package',contentOnly?'07_case_content_inputs':'.');
const originalRun = 'da57d29d-cf54-4c29-85ae-54260ef92dcd';
const protectedRuns=[originalRun,...(contentOnly?['657cb4b7-42e2-4ca0-8d74-0d62ff4c07f6']:[])];
const modelId = 'ollama:qwen3.5:latest';
const frozenDigest = '6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7';
const sha = data => createHash('sha256').update(data).digest('hex');
const manifest = JSON.parse(await fs.readFile(path.join(packageDir, 'package_manifest.json'), 'utf8'));
const records = await Promise.all(manifest.records.filter(r => ['B0', 'B1'].includes(r.release)).map(async r => {
  if (!r.path.startsWith('02_model_visible/') && r.path !== '04_challenge_evidence/IA-C01_desk_message.md')
    throw Error('Refusing non-model-visible evidence.');
  const data = await fs.readFile(path.join(packageDir, r.path));
  if(contentOnly&&sha(data)!==r.sha256)throw Error('Prepared case-content hash differs: '+r.id);
  return { ...r, data, sha256: sha(data) };
}));
if (records.length !== 11 || records.filter(r => r.release === 'B1').length !== 4)
  throw Error('Unexpected B0+B1 inventory.');
const tagsResponse = await fetch('http://127.0.0.1:11434/api/tags');
if (!tagsResponse.ok) throw Error('Ollama unavailable.');
const installed = (await tagsResponse.json()).models.find(m => m.name === modelId.slice(7));
if (installed?.digest !== frozenDigest) throw Error('Model does not match the frozen Qwen digest.');
const codePaths = execFileSync('rg', ['--files', 'src', 'prompts', 'app'], {encoding: 'utf8'}).trim().split('\n')
  .concat(['package.json', 'package-lock.json', 'vite.config.ts', 'wrangler.local.json',
    'scripts/launch-supervised-b1.mjs','scripts/prepare-case-content-inputs.mjs']).sort();
const codeHashes = Object.fromEntries(await Promise.all(codePaths.map(async p => [p, sha(await fs.readFile(p))])));
const output = await fs.mkdtemp(path.join(root, contentOnly?'outputs/case-content-b1-':'outputs/supervised-b1-'));
async function record(name, value) {
  await fs.writeFile(path.join(output, name), JSON.stringify(value, null, 2) + '\n', {flag: 'wx'});
}
await record('frozen-inputs.json', {
  createdAt: new Date().toISOString(), protocol: 'Supervised cumulative B0+B1 initial pass; NOT the original B0-to-B1 V2 benchmark',
  modelId, modelDigest: frozenDigest, originalRun, protectedRuns,codeHashes,
  inputView:contentOnly?'case-content-only':'original-labeled-records',
  readingCheckpoint:!contentOnly,progressiveBoard:true,
  ...(contentOnly?{provenance:JSON.parse(await fs.readFile(path.join(packageDir,'provenance.operator-only.json'),'utf8'))}:{}),
  records: records.map(({id, release, scope, sha256}) => ({id, release, scope, sha256})),
  withheld: ['B2', 'B3', 'answer bank', 'ground truth', 'rubrics', 'previous model answers'],
  storyteller: false,
  interventions: ['Fresh current-engine track instead of mutating the incompatible old checkpoint.',
    'Operator attaches four scheduled B1 documents together, without inventing question IDs.',
    ...(contentOnly?[
      'User authorized disclaimer removal and a fresh V1; all original incident facts and source limitations remain.',
      'No earlier findings, answers, questions, board or task cache imported. Current generic progressive scheduler is unchanged.',
      'Case-local reference copies replace default library attachments for this new incident only; shared library unchanged.',
      'No automatic reading approval stop; user requested continuous execution.',
    ]:['Human inspection after original-document reading; no inference credited to Qwen when supplied by operator.'])],
});
await fs.writeFile(path.join(output, 'review-plan.md'), `# Operator review — never model input

This is a historically anchored synthetic reconstruction, not an actual plant investigation.
The production pipeline and prompts remain unchanged. B0+B1 is cumulative V1 on a new
track; do not score it as the original staged V2 or as an autonomous acceptance pass.
${contentOnly?'This fresh run uses case-content-only documents and the current progressive scheduler. No manual task selection or prior outputs are imported. The reading approval stop is disabled. The operator provenance audit is withheld from model input.':'The original-document reading approval checkpoint remains enabled.'}

## Review targets frozen before inference

- Preserve receiving service loss and maintenance context without inventing physical actions.
- Distinguish upstream and receiving pressure samples and point locations. Pursue physical
  paths and field states, preserving sampling and measurement-validity limitations.
- Interpret AL-44 using its registered P-R input, not its legacy COMP FAULT display text.
  Keep occurrence and acknowledgment times separate. The desk message is not a verified trip.
- Treat the work-document equipment omissions as a bounded observation about that revision.
  Request current installation/applicability evidence; do not declare a failed valve,
  inadequate procedure, worker error, or root cause from the omission alone.
- Preserve meaningful alternatives and cite every supported claim and relationship.
- Separate API/task completion, claim quality, and board completeness. A machine-supported
  claim is not human approval. Record overclaims verbatim; do not silently repair them.

## Later releases

B2/B3 stay withheld until this board is inspected. No storyteller, model fallback,
hidden truth, earlier model answers, or new synthetic answers are supplied.
`, {flag: 'wx'});

let proxy;
try {
  proxy = await getPlatformProxy({configPath: path.join(root, 'wrangler.local.json'),
    persist: {path: path.join(root, '.wrangler/state/v3')}, remoteBindings: false, envFiles: []});
  globalThis.__rcaOperatorBindings = proxy.env;
  registerHooks({load(url, context, next) {
    if (url === 'cloudflare:workers') return {format: 'module',
      source: 'export const env = globalThis.__rcaOperatorBindings;', shortCircuit: true};
    return next(url, context);
  }});
  const { createIncident, getIncident, initializeTrack, listReferenceDocuments } = await import('../src/server/repository.ts');
  const db = proxy.env.DB;
  const active = await db.prepare("SELECT id FROM engine_runs WHERE status IN ('queued','running')").all();
  if (active.results.length) throw Error('Another eligible investigation exists; refusing to dispatch mixed work.');
  const preservedBefore=await Promise.all(protectedRuns.map(id=>db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(id).first()));
  if (preservedBefore.some(r=>r?.status!=='paused')) throw Error('A protected checkpoint is not paused.');
  const references = await listReferenceDocuments();
  const intended = records.filter(r => r.scope === 'default_reference');
  if (references.length !== intended.length || references.some(d => d.extractionStatus !== 'ready' || !intended.some(r => (contentOnly?r.originalSha256:r.sha256) === d.sha256)))
    throw Error('Default reference library differs from the frozen package; nothing changed.');
  const libraryBefore=JSON.stringify(references);
  const incidentId = await createIncident(records.find(r => r.scope === 'incident_description').data.toString('utf8'), [modelId],
    records.filter(r => r.scope === 'starter_document').map(r => new File([r.data], path.basename(r.path), {type: 'text/markdown'})),
    {deferAnalysis: true, title: `${manifest.case_id} · ${contentOnly?'Clean-input':'Supervised'} B0+B1 · Qwen · ${new Date().toISOString()}`,
      ...(contentOnly?{referenceFiles:intended.map(r=>new File([r.data],path.basename(r.path),{type:'text/markdown'}))}:{})});
  const trackId = (await getIncident(incidentId)).tracks[0].id;
  await record('draft-identity.json', {incidentId, trackId, output});
  const statements = [];
  for (const r of records.filter(r => r.release === 'B1')) {
    const id = randomUUID(), name = path.basename(r.path), now = new Date().toISOString();
    const key = `question/${trackId}/${id}-${name}`;
    await proxy.env.FILES.put(key, r.data, {httpMetadata: {contentType: 'text/markdown'},
      customMetadata: {originalName: name, scope: 'question', incidentId, trackId, questionId: ''}});
    const saved = await proxy.env.FILES.get(key);
    if (!saved || sha(Buffer.from(await saved.arrayBuffer())) !== r.sha256) throw Error('Stored document hash mismatch.');
    statements.push(db.prepare(`INSERT INTO documents
      (id,scope,title,plant,incident_id,track_id,question_id,introduced_version,file_key,file_name,
       content_type,size,sha256,revision,extraction_status,extraction_notes,extracted_text,created_at)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).bind(id, 'question', name, 'General', incidentId, trackId,
        null, 1, key, name, 'text/markdown', r.data.length, r.sha256, '1', 'ready',
        'Scheduled evidence batch; lossless UTF-8 Markdown. No answer or question association invented.', r.data.toString('utf8'), now));
    statements.push(db.prepare(`INSERT INTO track_documents
      (id,track_id,document_id,source_scope,introduced_version,created_at) VALUES (?,?,?,?,?,?)`)
      .bind(randomUUID(), trackId, id, 'question', 1, now));
  }
  await db.batch(statements);
  const track = (await getIncident(incidentId)).tracks[0];
  const expected = records.filter(r => r.scope !== 'incident_description');
  const scopes = {default_reference: 'reference', starter_document: 'starter', answer_request_document: 'question'};
  if (track.versions.length || track.documents.length !== expected.length || track.documents.some(d =>
    !expected.some(r => r.sha256 === d.sha256 && scopes[r.scope] === d.scope) || d.questionId))
    throw Error('Draft evidence/scope verification failed. No inference queued.');
  if(JSON.stringify(await listReferenceDocuments())!==libraryBefore)throw Error('Shared reference library changed unexpectedly. No inference queued.');
  const initialized = await initializeTrack(trackId, true, {reviewAfterReading: !contentOnly});
  const run = await db.prepare('SELECT id FROM engine_runs WHERE track_id=?').bind(trackId).first();
  const preservedAfter=await Promise.all(protectedRuns.map(id=>db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(id).first()));
  if (JSON.stringify(preservedBefore) !== JSON.stringify(preservedAfter)) throw Error('A protected checkpoint changed unexpectedly.');
  const receipt = {incidentId, trackId, runId: run.id, initialized, output,
    dashboard: `http://localhost:3015/incident/${incidentId}`, originalUnchanged: true,protectedRunsUnchanged:protectedRuns,
    sharedReferenceLibraryUnchanged:true,inputView:contentOnly?'case-content-only':'original-labeled-records',
    documents: track.documents.map(d => ({id: d.id, title: d.title, scope: d.scope, sha256: d.sha256}))};
  await record('launch.json', receipt);
  console.log(JSON.stringify(receipt, null, 2));
} catch (error) {
  await record('launch-error.json', {at: new Date().toISOString(), error: String(error)});
  throw error;
} finally {
  await proxy?.dispose();
}
