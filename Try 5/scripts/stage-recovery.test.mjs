import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { causalReferenceProblems } from '../src/stages/causal-analysis/reference-contract.ts';
import { runCausalAnalysis } from '../src/stages/causal-analysis/run.ts';
import { deterministicBroker, runQuestionBroker } from '../src/stages/question-broker/run.ts';
import { brokerBatchProblems, brokerInBatches } from '../src/stages/question-broker/batches.ts';
import { causalCommitProblems } from '../src/orchestrator/commit-contract.ts';
import { runInvestigationCycle } from '../src/orchestrator/investigation-loop.ts';
import { brokerSchema, brokerSchemaFor, verificationSchema } from '../src/domain/schemas.ts';
import { z } from 'zod';
import { runCausalVerification } from '../src/stages/causal-verification/run.ts';
import { verificationReferenceProblems, verifiedTargetSets } from '../src/stages/causal-verification/reference-contract.ts';
import { verificationSchemaFor } from '../src/stages/causal-verification/output-schema.ts';

const model = { id: 'ollama:qwen3.5:latest', name: 'qwen3.5:latest', provider: 'ollama', available: true };
const decision = { summary: 'Contract test', evidenceUsed: [], unknowns: [], alternatives: [], confidence: 0.5 };
const fixture = new URL('../../R3 Benchmark Package/06_run_records/qwen-story-autonomous-N9Y0lS/latest-incident.json', import.meta.url);
const question = (i, intent = `branch-${i}`) => ({
  id: `q-${i}`, tagId: i % 2 ? 'stored-energy' : 'equipment-tool', proposedBy: 'equipment-tool',
  routedTo: [i % 2 ? 'stored-energy' : 'equipment-tool'],
  text: `What observation distinguishes ${intent}?`, intent, rationale: 'Distinguishes the specific physical mechanism.',
  evidenceNeeded: [`Evidence for ${intent}`], priority: 'high', status: 'proposed',
});
const keep = q => ({ candidateKey: q.id || q.candidateKey, disposition: 'keep', coveredByCandidateKey: '', reason: 'Distinct evidence boundary.' });
const payload = (output, done_reason = 'stop') => new Response(JSON.stringify({ message: { content: typeof output === 'string' ? output : JSON.stringify(output) }, done_reason }), { status: 200 });
const packetFrom = body => JSON.parse(body.messages[1].content.split('--- BEGIN EVIDENCE PACKET ---')[1].split('--- END EVIDENCE PACKET ---')[0]);
async function mocked(handler, work) {
  const original = globalThis.fetch;
  globalThis.fetch = async (_url, options) => handler(JSON.parse(options.body));
  try { return await work(); } finally { globalThis.fetch = original; }
}

test('actual failed Qwen drafts expose focal/reference defects without modifying history', async () => {
  const before = await fs.readFile(fixture);
  const saved = JSON.parse(before);
  const drafts = saved.incident.tracks[0].checkpoints.filter(c => c.stage === 'causal-analysis');
  assert.equal(drafts.length, 4);
  for (const draft of drafts) assert.ok(causalReferenceProblems(draft.payload.rawModelOutput).some(p => p.includes('focalKey')));
  for (let v = 1; v <= 4; v++) {
    const old = JSON.parse(await fs.readFile(new URL(`../../R3 Benchmark Package/06_run_records/qwen-followup/version-${v}.json`, import.meta.url)));
    assert.ok(causalCommitProblems(old.analysis).includes('Missing focal node.'));
  }
  assert.equal(createHash('sha256').update(await fs.readFile(fixture)).digest('hex'), createHash('sha256').update(before).digest('hex'));
});

test('the production causal stage rejects legacy output and accepts an explicit focal event from the same model', async () => {
  const saved = JSON.parse(await fs.readFile(fixture));
  const bad = saved.incident.tracks[0].checkpoints.find(c => c.stage === 'causal-analysis').payload.rawModelOutput;
  // Deliberate test fixture authored in the new protocol, not production repair.
  const { focalKey: oldPointer, nodes: oldNodes, ...rest } = structuredClone(bad);
  const oldKey = oldNodes[0].key;
  const focalEvent = { ...oldNodes[0] };
  delete focalEvent.key;
  delete focalEvent.type;
  const good = { ...rest, focalEvent, nodes: oldNodes.slice(1) };
  for (const edge of good.edges) {
    if ([oldPointer, oldKey].includes(edge.fromKey)) edge.fromKey = 'focal';
    if ([oldPointer, oldKey].includes(edge.toKey)) edge.toKey = 'focal';
  }
  const requests = [];
  const result = await mocked(body => {
    requests.push(body);
    return payload(requests.length === 1 ? bad : good);
  }, () => runCausalAnalysis(model, { originalIncident: 'Test only; never saved to the app.' }));
  assert.equal(requests.length, 2);
  assert.ok(requests.every(r => r.model === 'qwen3.5:latest' && r.format.properties.focalEvent && !r.format.properties.focalKey));
  assert.match(requests[1].messages[1].content, /focalEvent/);
  assert.equal(result.providerAttempts[0].raw, JSON.stringify(bad));
  assert.equal(result.trace.validation, 'repaired');
  assert.ok(result.board.nodes.some(node => node.id === result.board.focalNodeId));
});

test('unrepairable causal references fail after bounded attempts; no guessed focal node', async () => {
  let calls = 0;
  const bad = { maturity: 'initial', focalKey: 'missing', nodes: [], edges: [], questions: [], decision };
  await mocked(() => { calls++; return payload(bad); }, async () => {
    await assert.rejects(runCausalAnalysis(model, {}), /focalEvent/);
  });
  assert.equal(calls, 2);
});

test('reference validator rejects duplicate node keys and dangling edge endpoints', () => {
  const bad = { focalKey: 'f', nodes: [{ key: 'f', type: 'event', label: 'Fall' }, { key: 'f', type: 'event', label: 'Other' }], edges: [{ fromKey: 'absent', toKey: 'f' }] };
  assert.equal(causalReferenceProblems(bad).length, 2);
});

test('broker processes 75 distinct questions without a total cap and checks late cross-page duplicates', async () => {
  const candidates = Array.from({ length: 75 }, (_, i) => question(i));
  candidates.push(question(75, 'branch-0'));
  let calls = 0;
  const result = await mocked(body => {
    calls++;
    const p = packetFrom(body);
    assert.ok(p.candidates.length <= 4 && p.canonicalQuestions.length <= 16);
    const owners = [...p.canonicalQuestions];
    const decisions = p.candidates.map(q => {
      const owner = owners.find(other => other.intent === q.intent);
      if (owner) return { candidateKey: q.candidateKey, disposition: 'covered', coveredByCandidateKey: owner.candidateKey, reason: 'Identical intent, branch, decision and evidence request.' };
      owners.push(q);
      return keep(q);
    });
    return payload({ decisions, decision });
  }, () => runQuestionBroker(model, {}, candidates));
  assert.equal(result.questions.length, 75);
  assert.equal(result.skipped.length, 1);
  assert.equal(result.skipped[0].coveredByQuestionId, 'q-0');
  assert.deepEqual(new Set(result.questions[0].routedTo), new Set(['equipment-tool', 'stored-energy']));
  assert.equal(result.questions[0].text, candidates[0].text);
  assert.equal(result.batches.length, calls);
});

test('broker repairs missing decisions within the affected batch and never repeats an accepted batch', async () => {
  const calls = [];
  const candidates = Array.from({ length: 8 }, (_, i) => question(i));
  await mocked(body => {
    const p = packetFrom(body), first = p.candidates[0].candidateKey;
    calls.push(first);
    const decisions = p.candidates.map(keep);
    if (calls.length === 2) decisions.pop();
    return payload({ decisions, decision });
  }, async () => {
    const result = await runQuestionBroker(model, {}, candidates);
    assert.equal(result.questions.length, 8);
    assert.equal(result.trace.validation, 'repaired');
  });
  assert.deepEqual(calls, ['q-0', 'q-4', 'q-4']);
});

test('broker truncation preserves previous batches and fails closed after two attempts', async () => {
  const calls = [];
  await mocked(body => {
    const p = packetFrom(body), first = p.candidates[0].candidateKey;
    calls.push(first);
    return first === 'q-0' ? payload({ decisions: p.candidates.map(keep), decision }) : payload('{"decisions":[', 'length');
  }, async () => {
    await assert.rejects(runQuestionBroker(model, {}, Array.from({ length: 8 }, (_, i) => question(i))), error => {
      assert.equal(error.brokerBatches.length, 1);
      assert.equal(error.attempts.length, 2);
      return /token limit/.test(error.message);
    });
  });
  assert.deepEqual(calls, ['q-0', 'q-4', 'q-4']);
});

test('broker refuses omissions, cycles, unknown IDs and coverage of already answered questions', () => {
  const a = question(0), b = question(1);
  assert.ok(brokerBatchProblems({ decisions: [keep(a)] }, [a, b], []).length);
  const cover = (q, owner) => ({ ...keep(q), disposition: 'covered', coveredByCandidateKey: owner });
  assert.ok(brokerBatchProblems({ decisions: [cover(a, b.id), cover(b, a.id)] }, [a, b], []).length);
  assert.ok(brokerBatchProblems({ decisions: [cover(a, 'invented')] }, [a], []).length);
  assert.ok(brokerBatchProblems({ decisions: [cover({ ...a, status: 'answered' }, b.id)] }, [{ ...a, status: 'answered' }], [b]).length);
});

test('coverage chains across catalog pages resolve to the final retained owner', async () => {
  const candidates = Array.from({ length: 22 }, (_, i) => question(i));
  const result = await brokerInBatches(candidates, async (batch, catalog) => ({ decisions: batch.map(q => {
    if (q.id === 'q-21' && batch.some(q => q.id === 'q-20')) return { ...keep(q), disposition: 'covered', coveredByCandidateKey: 'q-20' };
    if (q.id === 'q-20' && catalog.some(q => q.id === 'q-17')) return { ...keep(q), disposition: 'covered', coveredByCandidateKey: 'q-17' };
    return keep(q);
  }) }));
  assert.equal(result.canonical.length, 20);
  assert.ok(result.covered.every(row => row.coveredByCandidateKey === 'q-17'));
});

test('strict production pipeline stops at the exhausted stage and preserves earlier checkpoints', async () => {
  const calls = [], checkpoints = [];
  const understanding = { summary: 'A beam fell.', focalEvent: 'A beam fell.', actualImpact: 'No injury reported.', potentialImpact: 'Impact exposure.', normalState: 'Not established.', eventState: 'Beam in pit.', understoodFacts: ['A beam fell.'], unknowns: ['Support state'], questions: [], decision };
  await mocked(body => {
    if (body.format.properties.focalEvent) { calls.push('understanding'); return payload(understanding); }
    calls.push('structuring'); return payload({});
  }, async () => {
    await assert.rejects(runInvestigationCycle({
      incident: 'A beam fell into a mill pit during outage preparation. No person was injured.', model,
      documents: [], strictExecution: true, onCheckpoint: async c => checkpoints.push(c),
    }));
  });
  assert.deepEqual(calls, ['understanding', 'structuring', 'structuring']);
  assert.equal(checkpoints.find(c => c.stage === 'incident-understanding').status, 'completed');
  assert.equal(checkpoints.find(c => c.stage === 'incident-structuring').status, 'failed');
  assert.ok(!checkpoints.some(c => c.stage === 'tagging' || c.stage === 'causal-analysis'));
});

test('API-compatible providers enforce the same causal-reference contract with bounded repair', async () => {
  const apiModel = { ...model, id: 'api:test-only', name: 'test-only', provider: 'openai-compatible', baseUrl: 'https://example.invalid', apiKey: 'test-placeholder' };
  const focalEvent = { label: 'A beam fell.', detail: 'Test fixture.', status: 'unknown', sourceIds: [], specialistIds: [] };
  const good = { maturity: 'initial', focalEvent, nodes: [], edges: [], questions: [], decision };
  let calls = 0;
  const result = await mocked(() => {
    calls++;
    return new Response(JSON.stringify({ choices: [{ message: { content: JSON.stringify(calls === 1 ? { ...good, focalKey: 'bad' } : good) }, finish_reason: 'stop' }] }));
  }, () => runCausalAnalysis(apiModel, {}));
  assert.equal(calls, 2); assert.equal(result.trace.validation, 'repaired');
  assert.ok(result.board.focalNodeId);
  assert.equal(result.providerAttempts.length, 2);
});

test('final deterministic deduplication preserves distinct questions with the same intent', () => {
  const a = question(0), b = { ...question(1, a.intent), text: 'What drawing defines the restraint capacity?', evidenceNeeded: ['Design drawing'] };
  assert.equal(deterministicBroker([a, b]).questions.length, 2);
  const identical = { ...a, id: 'duplicate', tagId: 'stored-energy', routedTo: ['stored-energy'] };
  const merged = deterministicBroker([a, identical]);
  assert.equal(merged.questions.length, 1);
  assert.deepEqual(new Set(merged.questions[0].routedTo), new Set(['equipment-tool', 'stored-energy']));
  assert.equal(merged.skipped[0].coveredByQuestionId, a.id);
});

test('broker decoding schema forbids the comma-joined IDs observed in the first live check', () => {
  const schema = brokerSchemaFor(['q-czy36u'], ['bq-1adc8hy', 'bq-rt3ptu', 'q-tgnqmy']);
  const row = { candidateKey: 'q-czy36u', disposition: 'covered', coveredByCandidateKey: 'bq-1adc8hy,bq-rt3ptu,q-tgnqmy', reason: 'Collective coverage is not one canonical owner.' };
  assert.equal(schema.safeParse({ decisions: [row], decision }).success, false);
  assert.equal(schema.safeParse({ decisions: [{ ...row, coveredByCandidateKey: 'q-tgnqmy' }], decision }).success, true);
  assert.equal(schema.safeParse({ decisions: [{ ...row, disposition: 'screened', coveredByCandidateKey: '' }], decision }).success, false);
  const generated = z.toJSONSchema(schema, { target: 'draft-7' });
  const alternatives = generated.properties.decisions.items.anyOf;
  assert.equal(alternatives[0].properties.disposition.const, 'keep');
  assert.equal(alternatives[0].properties.coveredByCandidateKey.const, '');
  assert.deepEqual(alternatives[1].properties.coveredByCandidateKey.enum, ['bq-1adc8hy', 'bq-rt3ptu', 'q-tgnqmy']);
});

test('exact failed answered-batch outputs are rejected by the decoding schema and repaired without losing answer identity', async () => {
  const file = new URL('../../R3 Benchmark Package/06_run_records/qwen-story-autonomous-A8rNaX/latest-incident.json', import.meta.url);
  const before = await fs.readFile(file);
  const failed = JSON.parse(before).incident.tracks[0].checkpoints.find(c => c.stage === 'question-broker' && c.status === 'failed');
  const outputs = failed.payload.providerAttempts.map(a => JSON.parse(a.raw));
  const ids = outputs[0].decisions.map(row => row.candidateKey);
  const schema = brokerSchemaFor(ids, [], ids);
  for (const output of outputs) {
    // Reproduces the old schema/runtime disagreement without editing a fixture.
    assert.equal(brokerSchema.safeParse(output).success, true);
    assert.equal(schema.safeParse(output).success, false);
  }
  const candidates = ids.map((id, index) => ({ ...question(index), id, status: 'answered' }));
  const corrected = { ...outputs[1], decisions: outputs[1].decisions.map(row => ({ ...row, coveredByCandidateKey: '' })) };
  assert.equal(schema.safeParse(corrected).success, true);
  const requests = [];
  const result = await mocked(body => {
    requests.push(body);
    const alternatives = body.format.properties.decisions.items.anyOf;
    assert.equal(alternatives.length, 4);
    assert.ok(alternatives.every(s => s.properties.disposition.const === 'keep' && s.properties.coveredByCandidateKey.const === ''));
    return payload(requests.length === 1 ? outputs[1] : corrected);
  }, () => runQuestionBroker(model, {}, candidates));
  assert.equal(requests.length, 2);
  assert.equal(result.trace.validation, 'repaired');
  assert.deepEqual(result.questions.map(q => [q.id, q.status, q.text, q.routedTo]), candidates.map(q => [q.id, q.status, q.text, q.routedTo]));
  assert.equal(result.skipped.length, 0);
  assert.equal(result.batches[0].providerAttempts[0].raw, JSON.stringify(outputs[1]));
  assert.deepEqual(await fs.readFile(file), before);
});

test('broker schema encodes disposition, owner order and answered identity together', () => {
  const a = { ...question(0), status: 'answered' }, b = question(1), c = question(2);
  const schema = brokerSchemaFor([a.id, b.id, c.id], ['catalog'], [a.id]);
  const valid = { decisions: [keep(a), { ...keep(b), disposition: 'covered', coveredByCandidateKey: a.id }, keep(c)], decision };
  assert.equal(schema.safeParse(valid).success, true);
  for (const [index, patch] of [
    [0, { disposition: 'covered', coveredByCandidateKey: 'catalog' }],
    [1, { disposition: 'keep', coveredByCandidateKey: a.id }],
    [1, { disposition: 'covered', coveredByCandidateKey: '' }],
    [1, { disposition: 'covered', coveredByCandidateKey: b.id }],
    [1, { disposition: 'covered', coveredByCandidateKey: c.id }],
    [1, { disposition: 'covered', coveredByCandidateKey: 'unknown' }],
  ]) {
    const bad = structuredClone(valid);
    Object.assign(bad.decisions[index], patch);
    assert.equal(schema.safeParse(bad).success, false);
  }
  const single = brokerSchemaFor([a.id], []);
  assert.equal(single.safeParse({ decisions: [keep(a)], decision }).success, true);
  assert.equal(z.toJSONSchema(single, { target: 'draft-7' }).properties.decisions.items.properties.coveredByCandidateKey.const, '');
});

test('exact live verification output retains board-ID decisions and cannot verify a blocked edge', async () => {
  const dir = new URL('../../R3 Benchmark Package/06_run_records/qwen-stage-recovery-tNJVPE/', import.meta.url);
  const causal = JSON.parse(await fs.readFile(new URL('causal.json', dir)));
  const verified = JSON.parse(await fs.readFile(new URL('verification.json', dir)));
  const keys = new Map(Object.entries(causal.keyToId));
  const result = await mocked(() => payload(verified.output), () => runCausalVerification(model, {}, causal.board, keys));
  assert.equal(result.board.nodes.filter(node => node.verified).length, 7);
  assert.equal(result.board.edges.filter(edge => edge.verified).length, 1);
  const blocked = result.board.verificationFindings.filter(f => f.severity === 'blocking').map(f => f.targetId);
  assert.ok(result.board.edges.every(edge => !blocked.includes(edge.id) || !edge.verified));
});

test('verification references accept valid legacy aliases but reject nonexistent nodes and edge indexes', () => {
  const board = { nodes: [{ id: 'node-f' }], edges: [{ id: 'edge-e', from: 'node-f', to: 'node-f' }] };
  const keys = new Map([['focal', 'node-f']]);
  const valid = { verifiedNodeKeys: ['focal'], verifiedEdgeIndexes: [0], findings: [] };
  assert.ok(verifiedTargetSets(valid, board, keys).nodes.has('node-f'));
  assert.ok(verificationReferenceProblems({ ...valid, verifiedNodeKeys: ['missing'], verifiedEdgeIndexes: [2] }, board, keys).length === 2);
});

test('verification decoding rejects the exact invented edge IDs and preserves bounded same-stage repair', async () => {
  const file = new URL('../../R3 Benchmark Package/06_run_records/qwen-story-autonomous-CDH6if/latest-incident.json', import.meta.url);
  const before = await fs.readFile(file);
  const checkpoints = JSON.parse(before).incident.tracks[0].checkpoints;
  const board = checkpoints.find(c => c.stage === 'causal-analysis').payload.board;
  const attempts = checkpoints.find(c => c.stage === 'causal-verification' && c.status === 'failed').payload.providerAttempts;
  const schema = verificationSchemaFor(board);
  for (const attempt of attempts) {
    assert.equal(verificationSchema.safeParse(JSON.parse(attempt.raw)).success, true);
    assert.equal(schema.safeParse(JSON.parse(attempt.raw)).success, false);
  }
  const good = JSON.parse(attempts[1].raw);
  // A controlled model-response fixture, not production ID correction. The
  // production mapper must never infer this relationship or rewrite an ID.
  const proceduralEdge = board.edges.find(e => e.from === 'node-1qd881d');
  good.findings.find(f => f.targetKey === 'edge-1qd881d').targetKey = proceduralEdge.id;
  const beforeBoard = structuredClone(board);
  const calls = [];
  const result = await mocked(body => {
    calls.push(body);
    assert.deepEqual(body.format.properties.verifiedNodeKeys.items.enum, board.nodes.map(n => n.id));
    const targets = body.format.properties.findings.items.properties.targetKey.enum;
    assert.deepEqual(new Set(targets), new Set([...board.nodes, ...board.edges].map(x => x.id)));
    assert.ok(!targets.includes('edge-1qd881d') && !targets.includes('edge-iqm0nn'));
    return payload(calls.length === 1 ? attempts[1].raw : good);
  }, () => runCausalVerification(model, {}, board, new Map()));
  assert.equal(calls.length, 2);
  assert.equal(result.trace.validation, 'repaired');
  assert.equal(result.providerAttempts[0].raw, attempts[1].raw);
  assert.equal(result.board.nodes.filter(n => n.verified).length, 1);
  assert.equal(result.board.edges.filter(e => e.verified).length, 0);
  assert.equal(result.board.verificationFindings.length, good.findings.length);
  assert.deepEqual(board, beforeBoard);
  assert.deepEqual(await fs.readFile(file), before);
});

test('verification does not normalize or accept unknown targets after exhausted repair', async () => {
  const board = { maturity: 'initial', focalNodeId: 'node-a', nodes: [{ id: 'node-a' }], edges: [], verificationFindings: [] };
  const bad = { maturity: 'initial', verifiedNodeKeys: [], verifiedEdgeIndexes: [], findings: [{ targetKey: 'edge-a', severity: 'blocking', issue: 'Unknown linkage.', evidenceNeeded: 'Drawing.', question: '' }], decision };
  let calls = 0;
  await mocked(() => { calls++; return payload(bad); }, async () => {
    await assert.rejects(runCausalVerification(model, {}, board, new Map()), error => {
      assert.equal(error.attempts.length, 2);
      assert.ok(error.attempts.every(a => a.raw.includes('edge-a')));
      return true;
    });
  });
  assert.equal(calls, 2);
  assert.deepEqual(board.verificationFindings, []);
});

test('verification schema permits honest empty results but rejects wrong-kind IDs and invalid indexes', () => {
  const board = { nodes: [{ id: 'node-a' }, { id: 'node-b' }], edges: [{ id: 'edge-ab' }] };
  const schema = verificationSchemaFor(board);
  const output = { maturity: 'initial', verifiedNodeKeys: [], verifiedEdgeIndexes: [], findings: [], decision };
  assert.equal(schema.safeParse(output).success, true);
  assert.equal(schema.safeParse({ ...output, verifiedNodeKeys: ['edge-ab'] }).success, false);
  for (const index of [-1, 0.5, 1]) assert.equal(schema.safeParse({ ...output, verifiedEdgeIndexes: [index] }).success, false);
  assert.equal(schema.safeParse({ ...output, verifiedEdgeIndexes: [0] }).success, true);
  const edgeless = verificationSchemaFor({ ...board, edges: [] });
  assert.equal(edgeless.safeParse(output).success, true);
  assert.equal(edgeless.safeParse({ ...output, verifiedEdgeIndexes: [0] }).success, false);
  assert.throws(() => verificationSchemaFor({ nodes: [], edges: [] }), /nonempty board/);
  assert.equal(z.toJSONSchema(edgeless, { target: 'draft-7' }).properties.verifiedEdgeIndexes.maxItems, 0);
});
