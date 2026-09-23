import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { z } from 'zod';
import { causalAnalysisSchema } from '../src/domain/schemas.ts';
import { causalOutputProblems, causalReferenceProblems, materializeCausalGraph } from '../src/stages/causal-analysis/reference-contract.ts';
import { runCausalAnalysis } from '../src/stages/causal-analysis/run.ts';
import { runCausalVerification } from '../src/stages/causal-verification/run.ts';
import { causalCommitProblems } from '../src/orchestrator/commit-contract.ts';

const file = new URL('../../R3 Benchmark Package/06_run_records/qwen-story-autonomous-pTsSr7/latest-incident.json', import.meta.url);
const model = { id: 'ollama:qwen3.5:latest', name: 'qwen3.5:latest', provider: 'ollama', available: true };
const decision = { summary: 'Contract fixture, not incident evidence.', evidenceUsed: [], unknowns: [], alternatives: [], confidence: 0.5 };
const focalEvent = { label: 'A beam fell.', detail: 'Cause remains unknown.', status: 'unknown', sourceIds: [], specialistIds: [] };
const base = () => ({ maturity: 'initial', focalEvent: { ...focalEvent }, nodes: [], edges: [], questions: [], decision });
const node = (key = 'support') => ({ ...focalEvent, key, type: 'condition', label: 'Support condition is unknown.' });
const edge = (fromKey = 'support', toKey = 'focal') => ({ fromKey, toKey, type: 'enabled', rationale: 'A candidate connection.', status: 'unknown', sourceIds: [], claimIds: [], counterfactual: 'Support could have remained sufficient.', competingExplanation: 'An independent release occurred.', evidenceGap: 'Support-state evidence.' });
async function mocked(handler, work) {
  const original = globalThis.fetch;
  globalThis.fetch = async (_url, options) => new Response(JSON.stringify({ message: { content: JSON.stringify(handler(JSON.parse(options.body))) }, done_reason: 'stop' }));
  try { return await work(); } finally { globalThis.fetch = original; }
}

test('explicit focal schema cannot express the saved dangling pointer or a missing focal object', async () => {
  const bytes = await fs.readFile(file);
  const failed = JSON.parse(bytes).incident.tracks[0].checkpoints.at(-1);
  for (const attempt of failed.payload.providerAttempts) {
    const output = JSON.parse(attempt.raw);
    assert.ok(causalReferenceProblems(output).some(p => p.includes('focalKey')));
    assert.equal(causalAnalysisSchema.safeParse(output).success, false);
  }
  const schema = z.toJSONSchema(causalAnalysisSchema, { target: 'draft-7' });
  assert.ok(schema.required.includes('focalEvent'));
  assert.equal(schema.properties.focalKey, undefined);
  assert.equal(schema.additionalProperties, false);
  assert.equal(schema.properties.focalEvent.additionalProperties, false);
  assert.equal(schema.properties.focalEvent.properties.key, undefined);
  assert.equal(schema.properties.focalEvent.properties.type, undefined);
  assert.equal(schema.properties.nodes.maxItems, 17);
  assert.ok(!schema.properties.nodes.items.properties.type.enum.includes('focal-event'));
  const good = base();
  for (const bad of [
    { ...good, focalKey: 'invented' },
    { ...good, focalEvent: undefined },
    { ...good, focalEvent: { ...good.focalEvent, key: 'invented' } },
    { ...good, nodes: [{ ...node(), type: 'focal-event' }] },
  ]) assert.equal(causalAnalysisSchema.safeParse(bad).success, false);
  assert.deepEqual(await fs.readFile(file), bytes);
});

test('explicit focal materialization preserves all 18 nodes and 11 edges from a controlled new-protocol fixture', async () => {
  const bytes = await fs.readFile(file);
  const old = JSON.parse(JSON.parse(bytes).incident.tracks[0].checkpoints.at(-1).payload.providerAttempts[0].raw);
  // The known event is explicitly selected HERE to author a new-protocol test
  // response. Production never guesses, converts or commits the failed output.
  const focal = old.nodes.find(n => n.key === 'event-fall');
  const content = { ...focal };
  delete content.key;
  delete content.type;
  const rest = { ...old };
  delete rest.focalKey;
  const output = causalAnalysisSchema.parse({ ...rest, focalEvent: content,
    nodes: old.nodes.filter(n => n !== focal),
    edges: old.edges.map(e => ({ ...e, fromKey: e.fromKey === 'event-fall' ? 'focal' : e.fromKey, toKey: e.toKey === 'event-fall' ? 'focal' : e.toKey })),
  });
  const before = structuredClone(output);
  const graph = materializeCausalGraph(output);
  assert.deepEqual(causalReferenceProblems(graph), []);
  assert.equal(graph.nodes.length, 18); assert.equal(graph.edges.length, 11);
  assert.deepEqual(graph.edges, output.edges);
  assert.deepEqual(graph.nodes.slice(1), output.nodes);
  assert.deepEqual(graph.nodes[0], { ...content, key: 'focal', type: 'focal-event' });
  const result = await mocked(() => output, () => runCausalAnalysis(model, {}));
  assert.equal(result.board.nodes.length, 18); assert.equal(result.board.edges.length, 11);
  assert.equal(result.board.focalNodeId, result.keyToId.get('focal'));
  assert.ok(result.board.edges.every(e => result.board.nodes.some(n => n.id === e.from) && result.board.nodes.some(n => n.id === e.to)));
  assert.deepEqual(result.output, before);
  assert.deepEqual(output, before);
  assert.deepEqual(await fs.readFile(file), bytes);
});

test('reserved-key collisions, duplicate keys, blank focal propositions and dangling edges still fail closed', () => {
  for (const output of [
    { ...base(), nodes: [node('focal')] },
    { ...base(), nodes: [node(), node()] },
    { ...base(), focalEvent: { ...focalEvent, label: '   ' } },
    { ...base(), edges: [edge('timeline-id')] },
  ]) assert.ok(causalOutputProblems(causalAnalysisSchema.parse(output)).length);
});

test('explicit uncertain focal needs no invented causes and retains stable application identity', async () => {
  const first = await mocked(() => base(), () => runCausalAnalysis(model, {}));
  const second = await mocked(() => ({ ...base(), focalEvent: { ...focalEvent, label: 'The same beam fell into the pit.' } }), () => runCausalAnalysis(model, {}));
  assert.equal(first.board.focalNodeId, second.board.focalNodeId);
  assert.equal(first.board.nodes[0].status, 'unknown');
  assert.equal(first.board.nodes[0].verified, false);
  assert.deepEqual(first.board.nodes[0].sourceIds, []);
  assert.deepEqual(first.board.edges, []);
  assert.deepEqual(first.output, base());
});

test('new-protocol causal stage preserves raw attempts and rejects dangling endpoints after two tries', async () => {
  const bad = { ...base(), nodes: [node()], edges: [edge('event-1794j8z')] };
  let calls = 0;
  await mocked(() => { calls++; return bad; }, async () => {
    await assert.rejects(runCausalAnalysis(model, {}), error => {
      assert.equal(error.attempts.length, 2);
      assert.ok(error.attempts.every(a => a.raw === JSON.stringify(bad)));
      return /nonexistent node/.test(error.message);
    });
  });
  assert.equal(calls, 2);
});

test('new-protocol focal and edges pass downstream verification without relaxing commit requirements', async () => {
  const output = { ...base(), nodes: [node()], edges: [edge()] };
  const causal = await mocked(() => output, () => runCausalAnalysis(model, {}));
  const verified = await mocked(body => {
    assert.ok(body.format.properties.verifiedNodeKeys.items.enum.includes(causal.board.focalNodeId));
    return { maturity: 'initial', verifiedNodeKeys: [], verifiedEdgeIndexes: [], findings: [], decision };
  }, () => runCausalVerification(model, {}, causal.board, causal.keyToId));
  const snapshot = { stageErrors: [], trace: [causal.trace, verified.trace], causalBoard: verified.board };
  assert.deepEqual(causalCommitProblems(snapshot), []);
  assert.ok(causalCommitProblems({ ...snapshot, trace: [causal.trace] }).includes('Causal verification did not complete.'));
  assert.ok(verified.board.nodes.every(n => !n.verified));
  assert.ok(verified.board.edges.every(e => !e.verified));
});
