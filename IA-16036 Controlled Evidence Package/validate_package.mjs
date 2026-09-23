// Read-only package checks. No app/API/model calls, no extraction or process launch.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const root = path.dirname(fileURLToPath(import.meta.url));
const read = (name) => fs.readFileSync(path.join(root, name), 'utf8');
const sha256 = (name) => createHash('sha256').update(fs.readFileSync(path.join(root, name))).digest('hex');
const manifest = JSON.parse(read('package_manifest.json'));
const rubric = JSON.parse(read('05_evaluation/rubric.json'));
const problems = [];
let checks = 0;
const check = (condition, message) => { checks++; if (!condition) problems.push(message); };
const ids = new Set();
const recordPaths = new Set();
const texts = new Map();
const counts = Object.fromEntries(manifest.release_order.map((batch) => [batch, 0]));

for (const record of manifest.records) {
  check(!ids.has(record.id), `Duplicate ID ${record.id}`);
  check(!recordPaths.has(record.path), `Duplicate path ${record.path}`);
  ids.add(record.id); recordPaths.add(record.path);
  const full = path.resolve(root, record.path);
  check(full.startsWith(root + path.sep), `Path outside package: ${record.path}`);
  check(/^(02_model_visible|04_challenge_evidence)\//.test(record.path), `Private file allowlisted: ${record.path}`);
  check(manifest.release_order.includes(record.release), `Invalid release: ${record.id}`);
  if (!fs.existsSync(full)) { check(false, `Missing ${record.path}`); continue; }
  const content = read(record.path);
  texts.set(record.id, content);
  check(content.includes(`Record ID: ${record.id}`), `Missing ID in ${record.path}`);
  check(content.includes('Synthetic evaluation record'), `Missing synthetic label: ${record.id}`);
  check(!/evaluator only|evaluator-only|Target T\d|rubric\.json|fixed_case_and_limits|Root Causal Factor One/i.test(content), `Possible evaluator text leaked: ${record.id}`);
  check(content.length < 160000, `Exceeds app text extraction cap: ${record.id}`);
  counts[record.release]++;
}

check(manifest.records.length === 18, 'Expected 18 records');
check(JSON.stringify(counts) === JSON.stringify({B0:7,B1:4,B2:4,B3:3}), 'Release counts changed');
const kickoff = manifest.records.filter((r) => r.release === 'B0').map((r) => texts.get(r.id)).join('\n');
check(!/V-201|V-202|boundary-impact|4-D|COMP FAULT/.test(kickoff), 'Later case-specific discriminator appeared in kickoff');
check(manifest.records.filter((r) => r.scope === 'default_reference').length === 3, 'Default count');
check(manifest.records.filter((r) => r.scope === 'starter_document').length === 3, 'Starter count');

check(rubric.criteria.reduce((sum, item) => sum + item.points, 0) === 100, 'Rubric not 100 points');
check(new Set(rubric.criteria.map((item) => item.id)).size === 16, 'Expected 16 unique targets');
const targets = read('05_evaluation/precise_review_targets.md');
for (const item of rubric.criteria) {
  check(targets.includes(`| ${item.id} |`), `Missing target ${item.id}`);
  check(manifest.release_order.includes(item.batch), `Invalid rubric batch ${item.id}`);
}
for (const [id, content] of texts) {
  for (const ref of content.match(/IA-[IDSPC]\d{2}/g) || []) {
    check(ids.has(ref), `Unknown record reference ${ref} in ${id}`);
  }
}
for (const template of ['question_export.template.json', 'answer_payload.template.json']) {
  const data = JSON.parse(read(`06_run_records/${template}`));
  check(data.template_only === true, `Template not marked: ${template}`);
  check((data.questions || data.answers).length === 0, `Invented run results in ${template}`);
}

// These checks catch edits to the intentional time/state relationships; they
// do not certify engineering validity or substitute for semantic review.
check(texts.get('IA-P01').includes('| 10:00:11 | 6.9 | 5.8 | 1 |'), 'Initial pressure relation changed');
check(texts.get('IA-P01').includes('| 10:06:20 | 6.9 | 6.0 | 1 |'), 'Recovery sample changed');
check(texts.get('IA-P05').includes('M-101 left closed; M-102 left open'), 'Recovery state changed');
check(texts.get('IA-P04').includes('| B-17a | H-U site header | V-201 | B-17 spool |'), 'First series segment changed');
check(texts.get('IA-P04').includes('| B-17b | B-17 spool | V-202 | H-R receiving header |'), 'Second series segment changed');

const controls = [
  'package_manifest.json',
  '01_withheld_ground_truth/historical_anchor.md',
  '01_withheld_ground_truth/fixed_case_and_limits.md',
  '03_answer_bank/answer_agent_rules.md',
  '03_answer_bank/question_source_index.md',
  '03_answer_bank/unavailable_facts.md',
  '05_evaluation/run_protocol.md',
  '05_evaluation/precise_review_targets.md',
  '05_evaluation/rubric.json',
  '05_evaluation/scoring_guide.md',
  'validate_package.mjs'
];
const hashes = Object.fromEntries([...manifest.records.map((r) => r.path), ...controls].sort().map((name) => [name, sha256(name)]));
const sealPath = path.join(root, 'package_seal.json');
let sealStatus = 'not_created';
if (fs.existsSync(sealPath)) {
  const seal = JSON.parse(read('package_seal.json'));
  check(JSON.stringify(Object.keys(seal.hashes).sort()) === JSON.stringify(Object.keys(hashes).sort()), 'Seal file set differs');
  for (const [name, hash] of Object.entries(hashes)) check(seal.hashes[name] === hash, `Seal mismatch ${name}`);
  sealStatus = problems.some((s) => s.startsWith('Seal')) ? 'mismatch' : 'matched';
}
console.log(JSON.stringify({case_id:manifest.case_id, checks, passed:problems.length===0, problems, record_count:ids.size, release_counts:counts, seal_status:sealStatus, hashes}, null, 2));
if (problems.length) process.exitCode = 1;
