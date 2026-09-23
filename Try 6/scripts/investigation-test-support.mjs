import fs from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { workerStep } from '../src/engine/tasks/worker.ts';
import { readState } from '../src/engine/tasks/artifacts.ts';

export function database() {
  const sqlite = new DatabaseSync(':memory:');
  for (const file of fs.readdirSync(new URL('../drizzle/', import.meta.url)).filter(n => n.endsWith('.sql')).sort())
    sqlite.exec(fs.readFileSync(new URL('../drizzle/' + file, import.meta.url), 'utf8'));
  return {
    prepare(sql) { let values = []; return {
      bind(...v) { values = v; return this; },
      async first() { return sqlite.prepare(sql).get(...values) || null; },
      async all() { return { results: sqlite.prepare(sql).all(...values), success: true, meta: {} }; },
      async run() { const r = sqlite.prepare(sql).run(...values); return { success: true, meta: { changes: Number(r.changes) }, results: [] }; },
    }; },
    async batch(statements) {
      sqlite.exec('BEGIN');
      try { const results = []; for (const s of statements) results.push(await s.run()); sqlite.exec('COMMIT'); return results; }
      catch (e) { sqlite.exec('ROLLBACK'); throw e; }
    },
    close() { sqlite.close(); },
  };
}
export const model = { id: 'ollama:test-only', name: 'Test fixture', provider: 'ollama', available: true,
  digest: 'test-immutable-digest', detail: 'Deterministic adapter, not model performance', contextWindow: 32768 };
export function document(id, text) { return { id, scope: 'starter', title: id, fileName: id+'.md', fileKey: id,
  contentType: 'text/markdown', size: text.length, sha256: id+text.length, revision: '1', plant: 'Test',
  extractionStatus: 'ready', extractionNotes: '', extractedText: text, createdAt: '2026-09-20T00:00:00Z' }; }
export const cases = [
  { incident: 'A carriage moved during maintenance. No injury was reported.',
    documents: [document('pressure', 'Gauge P1 indicated 4.5 bar at 10:00.'), document('background', 'The supplier office opens at 08:00.')],
    update: 'The carriage restraint was removed at 09:58, according to the signed inspection record.' },
  { incident: 'A container overflowed during a routine transfer.',
    documents: [document('level', 'The receiving vessel level read 95 percent at 14:05.'), document('background', 'The supplier office opens at 08:00.')],
    update: 'The signed inspection reports that the high-level alarm sounded before overflow.' },
];
const decision = { summary: 'Deterministic workflow fixture, not an RCA judgment.' };
export const finding = (statement, reference='S1') => ({ statement, kind: 'observation', subject: '', predicate: '', location: '',
  time: '', unit: '', qualifiers: '', references: [reference], tags: ['stored-energy'], replaces: null });
export const direction = (branch='mechanism', n=0, f=[]) => ({ branch, question: `Which original record resolves mechanism uncertainty ${n}?`,
  decision: `Distinguish the proposed mechanism from alternative ${n}.`, evidenceNeeded: `Supply the contemporaneous observation for uncertainty ${n}.`,
  ifPresent: 'Supports the proposed mechanism, subject to source verification.', ifAbsent: 'A reliable contrary observation would weaken this mechanism.',
  priority: 'discriminating', findings: f });

export function fixtureRunner(log, { fail=()=>false, questionCount=1, noConsult=false, omitOldBranch=false }={}) {
  return async request => {
    log.push(request);
    if (fail(request)) throw Error('Injected independent task failure');
    const kind = request.schemaName.replace('try6_', ''), p = request.evidencePacket;
    let output;
    if (kind === 'read') output = { findings: [finding(p.evidence[0].text, p.evidence[0].ref)],
      questions: [{ text: 'Reader should not fan out work', decision: 'Keep as a note', intent: '', subject: '', location: '', time: '', references: [] }], decision };
    if (kind === 'frame' || kind === 'refine') {
      const useful = p.notebook.filter(f => !f.sourceLabels.includes('background'));
      const changed = useful.find(f => f.sourceLabels.some(label => label.startsWith('Answer to ')));
      const known = useful.slice(0, 2).map(f => f.ref);
      if (changed) known.push(changed.ref);
      const branch = { id: 'mechanism', title: 'Candidate mechanism', mechanism: 'A test-only proposed mechanism to exercise evidence flow.',
        status: changed ? 'disfavored' : 'unresolved', supporting: known.slice(0,2), opposing: changed ? [changed.ref] : [],
        gap: changed ? 'The triggering sequence still requires a contemporaneous record.' : 'A contemporaneous observation is needed.',
        changeReason: changed ? 'The new answer weakens this fixture explanation; it does not prove another cause.' : 'Initial evidence is insufficient to establish a mechanism.' };
      output = { summary: 'A preliminary position with an open evidence direction.', focalEvent: useful[0]?.statement || 'Reported incident',
        normalState: 'Not established by this fixture.', eventState: 'Reported incident conditions.',
        tags: [{ id: 'stored-energy', reason: 'A relevant domain in this fixture.', findings: known.slice(0,2) }],
        nodes: known.map(finding => ({ finding, type: 'condition', reason: 'Needed to express the current position.' })),
        edges: [],
        branches: omitOldBranch && changed ? [] : [branch],
        consultations: noConsult ? [] : [{ branch: 'mechanism', domain: 'stored-energy', purpose: 'Check the specific mechanism ambiguity.', findings: known.slice(0,2) }],
        directions: Array.from({length: questionCount}, (_,n) => direction('mechanism',n,known.slice(0,2))), retiredNodes: [], withdrawnEdges: [], decision };
    }
    if (kind === 'connect') output = { edges: p.boardNodes.slice(0,2).map(n => ({ from: n.ref, to: 'EVENT', type: 'enabled', rationale: 'Test-only connection.',
      counterfactual: 'The event might not occur without this condition.', alternative: 'Another unknown condition could account for it.',
      gap: 'Mechanism requires a check.', findings: [n.ref] })), withdrawnEdges: [], nodeRequests: [], decision };
    if (kind === 'consult') output = { summary: 'The mechanism remains a possibility, not an established fact.',
      limitations: 'Specific original evidence is still needed.', findings: p.notebook.slice(0,2).map(f=>f.ref),
      directions: [direction('mechanism',0,p.notebook.slice(0,2).map(f=>f.ref))], decision };
    if (kind === 'resolve') {
      const answer = p.evidence.find(s => s.scope === 'answer');
      output = { answers: p.assignedQuestions.map(question => ({ question, status: answer ? 'answered' : 'not-found',
        answer: answer?.text || '', findings: answer ? p.notebook.filter(f=>f.sourceLabels.some(l=>l.startsWith('Answer to '))).map(f=>f.ref) : [],
        references: answer ? [answer.ref] : [], equivalentTo: null, evidenceNeeded: answer ? '' : 'Supply the requested contemporaneous observation.' })), decision };
    }
    if (kind === 'review') {
      const source = p.evidence.find(s => s.text.split('\n').map(l=>l.replace(/^\d+\|/,'')).join('\n').includes(p.target.statement)) || p.evidence[0];
      output = { targetStatement: p.target.statement, claimType: 'actual-state', establishes: 'Fixture assertion, not a semantic evaluation.',
        relation: 'entailed', evidence: [{ source: source.ref, lines: source.text.split('\n').flatMap((line,i)=>line.replace(/^\d+\|/,'').trim() ? [i+1] : []) }],
        missingPremises: [], evidenceConflicts: [], reason: 'Deterministic citation gate test.', questions: [], decision };
    }
    if (kind === 'verify') output = { status: 'supported', reason: 'Deterministic verification fixture, not model reasoning.',
      supporting: [p.evidence[0].ref], opposing: [], questions: [], decision };
    if (kind === 'actions') output = { actions: [], decision };
    if (!output) throw Error(`Fixture lacks ${kind}`);
    request.schema.parse(output);
    return { output, durationMs: 1, engine: 'deterministic-fixture', validation: 'valid', usage: { inputTokens: 100, outputTokens: 30 } };
  };
}
export async function drain(store, runner) {
  // This is a test watchdog to detect nontermination, not an application limit.
  for (let i=0; i<250; i++) { const r=await workerStep(store, async()=>model, runner); if (r.idle) return; }
  throw Error('Test watchdog: the investigation did not publish.');
}
export async function savedState(db, track='track') {
  const row=await db.prepare('SELECT state_json FROM engine_runs WHERE track_id=? ORDER BY number DESC LIMIT 1').bind(track).first();
  return readState(db,row.state_json);
}
