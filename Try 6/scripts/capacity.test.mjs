import test from 'node:test';
import assert from 'node:assert/strict';
import { z } from 'zod';
import { contextCapacity, planContext, inputByteCapacity } from '../src/engine/context/planner.ts';
import { ollamaContextWindow, readOllamaMetadata } from '../src/providers/ollama-metadata.ts';
import { ollamaProvider } from '../src/providers/ollama.ts';
import { openAiCompatibleProvider } from '../src/providers/openai-compatible.ts';
import { EvidenceIndex } from '../src/knowledge/retrieval/index.ts';
import { registerSources } from '../src/knowledge/sources/registry.ts';
import { database, model, document } from './investigation-test-support.mjs';
import { storeDocumentText, readDocumentText } from '../src/server/document-text-storage.ts';
import { putJSON, readJSON } from '../src/engine/tasks/artifacts.ts';
import { storyPacket, answerStoryBatch } from '../src/story-agent/run.ts';
import { enqueueRevision, latestInput } from '../src/server/engine-repository.ts';
import { loadDocumentMedia } from '../src/server/document-media.ts';

const hosted = { id: 'test-hosted', name: 'test-hosted', provider: 'openai-compatible', available: true,
  baseUrl: 'https://provider.invalid/v1', apiKey: 'test-only-no-real-credential', apiMode: 'responses' };
const schema = z.object({ answer: z.string() });
const request = { stage: 'causal-analysis', systemPrompt: 'Test contract.', evidencePacket: { question: 'test' },
  schema, schemaName: 'test', noTruncation: true, maxAttempts: 1 };

test('native context uses text architecture, not an encoder or original RoPE length', () => {
  assert.equal(ollamaContextWindow({ 'general.architecture': 'qwen35', 'qwen35.context_length': 262144,
    'clip.context_length': 77, 'qwen35.rope.scaling.original_context_length': 4096 }), 262144);
  assert.equal(ollamaContextWindow({ 'llama.context_length': 131072 }), 131072);
  assert.equal(ollamaContextWindow({ 'clip.context_length': 77 }), undefined);
  assert.equal(ollamaContextWindow({ 'a.context_length': 4096, 'b.context_length': 8192 }), undefined);
  assert.equal(ollamaContextWindow({ 'general.architecture': 'qwen35', 'qwen35.context_length': -1 }), undefined);
});

test('metadata discovery reads /api/show and caches by model digest, never model name alone', async () => {
  const original = globalThis.fetch, calls = [];
  globalThis.fetch = async (url, init) => { calls.push({ url, init }); return Response.json({ capabilities: ['completion', 'vision'],
    model_info: { 'general.architecture': 'qwen35', 'qwen35.context_length': 262144 } }); };
  try {
    assert.equal((await readOllamaMetadata('qwen-test', 'digest-a')).contextWindow, 262144);
    assert.deepEqual((await readOllamaMetadata('qwen-test', 'digest-a')).capabilities, ['completion','vision']);
    assert.equal(calls.length, 1);
    await readOllamaMetadata('qwen-test', 'digest-b'); assert.equal(calls.length, 2);
    assert.ok(calls.every(c => c.url.endsWith('/api/show')));
  } finally { globalThis.fetch = original; }
});

test('unknown hosted capacity is provider-managed, not a fabricated 32K limit', () => {
  assert.equal(contextCapacity(hosted), undefined);
  assert.equal(inputByteCapacity(hosted), Infinity);
  assert.throws(() => contextCapacity({ ...hosted, contextWindow: -1 }), /Invalid/);
  const packet = planContext({ model: hosted, system: '', schema, base: { notebook: 'e'.repeat(100_000) },
    index: new EvidenceIndex([]), query: '', required: [] });
  assert.equal(packet.packet.notebook.length, 100_000);
  assert.equal(packet.outputTokens, undefined);
});

test('262K context admits a notebook rejected by 32K; required evidence is never silently dropped', async () => {
  const registered = await registerSources({ incident: 'A test event.', model, answers: [], documents: [document('required', 'Original support.')] });
  const index = new EvidenceIndex(registered.sources), required = index.spans.map(s => s.id);
  const options = { model, system: '', schema, base: { notebook: 'n'.repeat(100_000) }, index, query: '', required };
  assert.throws(() => planContext(options), /metadata alone/);
  const large = planContext({ ...options, model: { ...model, contextWindow: 262144 } });
  assert.equal(large.selected.length, required.length); assert.equal(large.omitted.length, 0);
  assert.throws(() => planContext({ ...options, base: {}, required: ['missing'] }), /missing/);
});

test('input planner no longer withholds half or a quarter of the window for output', () => {
  const packet = planContext({ model, system: '', schema, base: { notebook: 'x'.repeat(50_000) },
    index: new EvidenceIndex([]), query: '', required: [] });
  assert.equal(packet.packet.notebook.length, 50_000);
  assert.ok(packet.outputTokens > 0);
});

test('exact source-dependent schema counts before evidence selection, not after', async () => {
  const registered = await registerSources({ incident: 'Test event.', model, answers: [], documents: [document('support', 'Original support.')] });
  const index = new EvidenceIndex(registered.sources);
  const options = { model, system: '', schema, base: {}, index, query: 'support', required: [],
    schemaForEvidence: spans => z.object({ answer: z.string().describe('x'.repeat(spans.length * 70_000)) }) };
  const packet = planContext(options);
  assert.equal(packet.selected.length, 0); assert.ok(packet.omitted.length > 0);
  assert.throws(() => planContext({ ...options, required: [index.spans[0].id] }), /Required joint evidence/);
});

test('Ollama sends the native window, unbounded generation, no shifting, and caller cancellation', async () => {
  const original = globalThis.fetch, controller = new AbortController(); let sent, signal;
  globalThis.fetch = async (_url, init) => { sent = JSON.parse(init.body); signal = init.signal;
    return new Response(JSON.stringify({ message: { content: '{"answer":"ok"}' }, done: true, done_reason: 'stop' }) + '\n'); };
  try {
    const result = await ollamaProvider.run({ ...request, model: { ...model, contextWindow: 262144 }, outputTokens: 3200, signal: controller.signal });
    assert.equal(result.output.answer, 'ok'); assert.equal(sent.options.num_ctx, 262144);
    assert.equal(sent.options.num_predict, -1); assert.equal(sent.truncate, false); assert.equal(sent.shift, false);
    controller.abort(); assert.equal(signal.aborted, true);
  } finally { globalThis.fetch = original; }
});

for (const apiMode of ['responses', 'chat-completions']) test(`${apiMode} has no output cap or timer; respects cancellation`, async () => {
  const original = globalThis.fetch, timeout = AbortSignal.timeout, controller = new AbortController(); let sent;
  AbortSignal.timeout = () => { throw Error('Unexpected application timer'); };
  globalThis.fetch = async (_url, init) => { sent = JSON.parse(init.body); assert.equal(init.signal, controller.signal);
    return Response.json(apiMode === 'responses' ? { status: 'completed', output_text: '{"answer":"ok"}' }
      : { choices: [{ message: { content: '{"answer":"ok"}' }, finish_reason: 'stop' }] }); };
  try {
    const result = await openAiCompatibleProvider.run({ ...request, model: { ...hosted, apiMode }, outputTokens: 3200, signal: controller.signal });
    assert.equal(result.output.answer, 'ok'); assert.equal(sent.max_output_tokens, undefined); assert.equal(sent.max_completion_tokens, undefined);
    if (apiMode === 'responses') assert.equal(sent.truncation, 'disabled');
  } finally { globalThis.fetch = original; AbortSignal.timeout = timeout; }
});

test('hosted cancellation cannot start a repair retry', async () => {
  const original = globalThis.fetch, controller = new AbortController(); let calls = 0;
  globalThis.fetch = async () => { calls++; controller.abort(); throw Error('Cancelled'); };
  try {
    await assert.rejects(() => openAiCompatibleProvider.run({ ...request, model: hosted, signal: controller.signal, maxAttempts: 5 }), /Cancelled/);
    assert.equal(calls, 1);
  } finally { globalThis.fetch = original; }
});

test('provider context/output rejection remains explicit and incomplete JSON is never applied', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => Response.json({ status: 'incomplete', output_text: '{"answer":"partial"}' });
  try { await assert.rejects(() => openAiCompatibleProvider.run({ ...request, model: hosted }), /before completion/); }
  finally { globalThis.fetch = original; }
});

test('larger extracted text and extraction cache round-trip without D1-sized rows', async () => {
  const db = database(), text = 'Original pressure reading 4.5 bar. 😀\n'.repeat(90_000);
  try {
    const stored = await storeDocumentText(db, text);
    assert.ok(stored.length < 1024); assert.equal(await readDocumentText(db, stored), text);
    assert.equal(await readDocumentText(db, 'Legacy plain text.'), 'Legacy plain text.');
    const cache = await putJSON(db, { text, status: 'ready', notes: '' });
    assert.ok(cache.length < 1024); assert.equal((await readJSON(db, cache)).text, text);
    const rows = await db.prepare('SELECT content FROM engine_artifact_chunks').all();
    assert.ok(rows.results.every(r => Buffer.byteLength(r.content) < 2_000_000));
  } finally { db.close(); }
});

test('media larger than 12MB per file and 24MB per batch is loaded intact, not silently skipped', async () => {
  const bytesA = new Uint8Array(17 * 1024 * 1024), bytesB = new Uint8Array(9 * 1024 * 1024);
  bytesA[0] = 42; bytesA[bytesA.length-1] = 21; bytesB[bytesB.length-1] = 99;
  const originals = new Map([['a', bytesA.buffer], ['b', bytesB.buffer]]);
  const documents = [...originals].map(([id, buffer]) => ({ ...document(id, ''), contentType: 'image/png', size: buffer.byteLength }));
  const loaded = await loadDocumentMedia(documents, new Set(), async id => ({ arrayBuffer: async () => originals.get(id) }));
  assert.equal(loaded.length, 2);
  assert.deepEqual(Buffer.from(loaded[0].dataBase64, 'base64'), Buffer.from(bytesA));
  assert.deepEqual(Buffer.from(loaded[1].dataBase64, 'base64'), Buffer.from(bytesB));
});

test('story packet has no 80-percent quota and never exposes hidden truth', () => {
  const text = 'Pressure reading and maintenance history.\n'.repeat(1050);
  const scenario = { title: 'Test', hiddenTruth: 'PRIVATE', sources: [{ id: 's', title: 'Pressure', sourceClass: 'test', available: true, text }] };
  const packet = storyPacket(model, scenario, { id: 'q', text: 'pressure' }, []);
  assert.equal(packet.passageCatalog.map(p => p.quote).join(''), text);
  assert.ok(!JSON.stringify(packet).includes('PRIVATE'));
});

test('story answers inherit the uncapped provider policy and cancellation signal', async () => {
  const original = globalThis.fetch, controller = new AbortController(); let sent;
  const scenario = { title: 'Test', hiddenTruth: 'PRIVATE', sources: [{ id: 's', title: 'Pressure', sourceClass: 'test', available: true, text: 'Pressure unknown.' }] };
  globalThis.fetch = async (_url, init) => { sent = JSON.parse(init.body); assert.equal(init.signal, controller.signal);
    return Response.json({ status: 'completed', output_text: JSON.stringify({ answers: [{ questionId: 'q', status: 'unknown',
      answer: 'The supplied record does not establish the pressure.', passageIds: [], limitation: 'No measurement.' }] }) }); };
  try {
    const result = await answerStoryBatch(hosted, scenario, [{ id: 'q', text: 'pressure?' }], [], [], controller.signal);
    assert.equal(result.output.answers.length, 1); assert.equal(sent.max_output_tokens, undefined);
  } finally { globalThis.fetch = original; }
});

test('a track freezes its native context; subsequent metadata cannot silently change historical configuration', async () => {
  const db = database();
  try {
    await enqueueRevision(db, 'native', 'Test incident.', { ...model, contextWindow: 262144 }, []);
    await enqueueRevision(db, 'native', 'Test incident.', { ...model, contextWindow: 32768 }, []);
    assert.equal((await latestInput(db, 'native')).input.model.contextWindow, 262144);
  } finally { db.close(); }
});
