import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn } from 'node:child_process';

const packageRoot = '/Users/dhwanilchauhan/Desktop/RCA Try 1/R3 Benchmark Package';
const appUrl = process.env.TRY4_URL || 'http://localhost:3001';
const modelId = process.argv[2];
const campaign = process.env.R3_CAMPAIGN || 'try4-ground-truth-benchmark-2026-09-08';
const requestTimeoutSeconds = Number(process.env.R3_REQUEST_TIMEOUT_SECONDS || 14_400);

if (!modelId?.startsWith('ollama:')) {
  throw new Error('Usage: node run_one_try4_model.mjs ollama:<model-tag>');
}

const modelSlug = modelId.slice('ollama:'.length).replace(/[^a-zA-Z0-9._-]/g, '_');
const runDir = path.join(packageRoot, '06_run_records', campaign, modelSlug);
await fs.mkdir(runDir, { recursive: true });

const incidentPath = path.join(packageRoot, '02_model_visible/00_incident_input/incident_summary.txt');
const starterDir = path.join(packageRoot, '02_model_visible/02_starter_documents');
const originalDir = path.join(packageRoot, '02_model_visible/03_progressive_evidence/original_synthetic_set');
const derivedDir = path.join(packageRoot, '02_model_visible/03_progressive_evidence/ground_truth_derived');
const challengeDir = path.join(packageRoot, '04_challenge_evidence');

// Exactly 24 incident records are attached. With the eight default references
// already registered in Try 4, this fills the harness's 32-source adjudication window.
const relativeInputs = [
  '02_model_visible/02_starter_documents/Initial_Evidence_Register.pdf',
  '02_model_visible/02_starter_documents/Initial_Scene_Sketch_and_Timeline.pdf',
  '02_model_visible/02_starter_documents/Preliminary_Incident_Notification_16515.pdf',
  '02_model_visible/03_progressive_evidence/ground_truth_derived/GTDE-01_configuration_and_travel_observation.md',
  '02_model_visible/03_progressive_evidence/ground_truth_derived/GTDE-02_extended_video_review.md',
  '02_model_visible/03_progressive_evidence/ground_truth_derived/GTDE-03_hydraulic_isolation_followup.md',
  '02_model_visible/03_progressive_evidence/ground_truth_derived/GTDE-04_mechanical_design_and_retention_review.md',
  '02_model_visible/03_progressive_evidence/ground_truth_derived/GTDE-05_task_loto_review.md',
  '02_model_visible/03_progressive_evidence/ground_truth_derived/GTDE-06_measurement_and_condition_summary.md',
  '04_challenge_evidence/01_Superseded_Similar_Stand_Drawing_Note.pdf',
  '04_challenge_evidence/02_Anonymous_Turnover_Note.pdf',
  '04_challenge_evidence/03_Unverified_Crane_Rumor_Email.pdf',
  '02_model_visible/03_progressive_evidence/original_synthetic_set/01_Mechanical_Assembly_and_Retention_Record.pdf',
  '02_model_visible/03_progressive_evidence/original_synthetic_set/02_Energy_Control_Plan.pdf',
  '02_model_visible/03_progressive_evidence/original_synthetic_set/03_Lockout_Verification_Record.pdf',
  '02_model_visible/03_progressive_evidence/original_synthetic_set/04_Shift_Turnover_Log.pdf',
  '02_model_visible/03_progressive_evidence/original_synthetic_set/05_Outage_Work_Scope_and_Sequence.pdf',
  '02_model_visible/03_progressive_evidence/original_synthetic_set/06_JJHAC_JSHA_Record.pdf',
  '02_model_visible/03_progressive_evidence/original_synthetic_set/07_Witness_Statement_Packet.pdf',
  '02_model_visible/03_progressive_evidence/original_synthetic_set/08_Crane_Activity_Log.pdf',
  '02_model_visible/03_progressive_evidence/original_synthetic_set/09_Hydraulic_Status_and_Bleed_Verification.pdf',
  '02_model_visible/03_progressive_evidence/original_synthetic_set/10_Scene_Photo_Index_and_Measurement_Log.pdf',
  '02_model_visible/03_progressive_evidence/original_synthetic_set/11_Post_Event_Mechanical_Inspection.pdf',
  '02_model_visible/03_progressive_evidence/original_synthetic_set/15_Video_Review_Log.pdf',
];

function mime(fileName) {
  if (fileName.endsWith('.pdf')) return 'application/pdf';
  if (fileName.endsWith('.md')) return 'text/markdown';
  if (fileName.endsWith('.txt')) return 'text/plain';
  return 'application/octet-stream';
}

async function digest(filePath) {
  return crypto.createHash('sha256').update(await fs.readFile(filePath)).digest('hex');
}

async function jsonFetch(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  let payload;
  try { payload = JSON.parse(text); }
  catch { payload = { raw: text }; }
  if (!response.ok) throw new Error(`${response.status} ${JSON.stringify(payload).slice(0, 2000)}`);
  return payload;
}

async function createIncidentWithCurl(descriptionFile, inputs) {
  const args = [
    '--silent', '--show-error', '--max-time', String(requestTimeoutSeconds),
    '--request', 'POST', `${appUrl}/api/incidents`,
    '--form', `description=<${descriptionFile}`,
    '--form', `modelIds=${JSON.stringify([modelId])}`,
  ];
  for (const input of inputs) {
    args.push('--form', `files=@${input.absolute};type=${mime(input.absolute)}`);
  }
  args.push('--write-out', '\n%{http_code}');

  const child = spawn('/usr/bin/curl', args, { stdio: ['ignore', 'pipe', 'pipe'] });
  let stdout = '';
  let stderr = '';
  child.stdout.on('data', (chunk) => { stdout += chunk.toString(); });
  child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });
  const exitCode = await new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('close', resolve);
  });
  const split = stdout.lastIndexOf('\n');
  const body = split >= 0 ? stdout.slice(0, split) : stdout;
  const status = Number(split >= 0 ? stdout.slice(split + 1).trim() : 0);
  let payload;
  try { payload = JSON.parse(body); }
  catch { payload = { raw: body }; }
  if (exitCode !== 0 || status < 200 || status >= 300) {
    throw new Error(`curl exit ${exitCode}; HTTP ${status}; ${stderr}; ${JSON.stringify(payload).slice(0, 2000)}`);
  }
  return payload;
}

const description = (await fs.readFile(incidentPath, 'utf8')).trim();
const inputFiles = relativeInputs.map((relative) => ({
  relative,
  absolute: path.join(packageRoot, relative),
}));

for (const input of inputFiles) await fs.access(input.absolute);

const inputManifest = {
  campaign,
  modelId,
  appUrl,
  requestTimeoutSeconds,
  mode: 'standardized evidence-complete creation run',
  defaultReferenceCountExpected: 8,
  incidentDocumentCount: inputFiles.length,
  withheldGroundTruthSupplied: false,
  incidentSha256: await digest(incidentPath),
  files: await Promise.all(inputFiles.map(async (input) => ({
    path: input.relative,
    sha256: await digest(input.absolute),
    bytes: (await fs.stat(input.absolute)).size,
  }))),
  startedAt: new Date().toISOString(),
};
await fs.writeFile(path.join(runDir, 'input-manifest.json'), JSON.stringify(inputManifest, null, 2));

const started = Date.now();
console.log(JSON.stringify({ event: 'run-started', modelId, runDir, inputFiles: inputFiles.length }));
const heartbeat = setInterval(() => {
  console.log(JSON.stringify({ event: 'heartbeat', modelId, elapsedSeconds: Math.round((Date.now() - started) / 1000) }));
}, 30_000);

try {
  const creation = await createIncidentWithCurl(incidentPath, inputFiles);
  await fs.writeFile(path.join(runDir, 'create-response.json'), JSON.stringify(creation, null, 2));
  const incident = await jsonFetch(`${appUrl}/api/incidents/${creation.id}`);
  await fs.writeFile(path.join(runDir, 'incident.json'), JSON.stringify(incident, null, 2));

  const track = incident.incident?.tracks?.[0];
  const version = track?.versions?.at(-1);
  if (version) await fs.writeFile(path.join(runDir, `version-${version.number}.json`), JSON.stringify(version, null, 2));

  const analysis = version?.analysis;
  const summary = {
    campaign,
    modelId,
    incidentId: creation.id,
    trackId: track?.id,
    version: version?.number,
    elapsedSeconds: Math.round((Date.now() - started) / 1000),
    status: analysis?.status,
    checkpoints: track?.checkpoints?.length ?? 0,
    failedCheckpoints: track?.checkpoints?.filter((item) => item.status === 'failed').length ?? 0,
    blockedCheckpoints: track?.checkpoints?.filter((item) => item.status === 'blocked').length ?? 0,
    stageErrors: analysis?.stageErrors?.length ?? 0,
    tags: analysis?.tags?.map((tag) => tag.id) ?? [],
    questions: analysis?.questions?.length ?? 0,
    skippedQuestions: analysis?.skippedQuestions?.length ?? 0,
    sourceAssessments: analysis?.sourceAssessments?.length ?? 0,
    adjudicationConflicts: analysis?.adjudicationConflicts?.length ?? 0,
    evidenceClaims: analysis?.evidenceClaims?.length ?? 0,
    claimConflicts: analysis?.conflicts?.length ?? 0,
    causalNodes: analysis?.causalBoard?.nodes?.length ?? 0,
    causalEdges: analysis?.causalBoard?.edges?.length ?? 0,
    causalMaturity: analysis?.causalBoard?.maturity,
    verificationFindings: analysis?.causalBoard?.verificationFindings?.length ?? 0,
    correctiveActions: analysis?.correctiveActions?.length ?? 0,
    completedAt: new Date().toISOString(),
  };
  await fs.writeFile(path.join(runDir, 'summary.json'), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify({ event: 'run-completed', ...summary }));
} catch (error) {
  const failure = {
    campaign,
    modelId,
    elapsedSeconds: Math.round((Date.now() - started) / 1000),
    error: error instanceof Error ? error.message : String(error),
    failedAt: new Date().toISOString(),
  };
  await fs.writeFile(path.join(runDir, 'failure.json'), JSON.stringify(failure, null, 2));
  console.error(JSON.stringify({ event: 'run-failed', ...failure }));
  process.exitCode = 1;
} finally {
  clearInterval(heartbeat);
}
