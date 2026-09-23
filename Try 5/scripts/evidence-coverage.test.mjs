import test from 'node:test';
import assert from 'node:assert/strict';
import { buildEvidenceSegments, EVIDENCE_CHUNK_CHARACTERS } from '../src/knowledge/evidence-segments.ts';
import { retrieveForQuestion } from '../src/knowledge/retrieval.ts';
import { assertPacketFits, MAX_STAGE_PACKET_CHARACTERS } from '../src/knowledge/packet-limits.ts';
import { evidencePacket } from '../src/orchestrator/investigation-loop.ts';
import { runEvidenceAdjudication } from '../src/stages/evidence-adjudication/run.ts';
import { promptFor, PROMPT_VERSION } from '../src/prompts/manifest.ts';

const doc = (text, id = 'doc-1') => ({ id, title: id, scope: 'starter', revision: 'test', extractedText: text });

test('every character survives chunking, including preamble, repeated markers and tail', () => {
  const text = '  Preamble\n' + ('R3-EV-001 repeated marker\n' + 'x'.repeat(400) + '\n').repeat(20) + 'END qualification  \n';
  const segments = buildEvidenceSegments([doc(text)]);
  assert.equal(segments.map(s => s.excerpt).join(''), text);
  assert.equal(new Set(segments.map(s => s.sourceId)).size, segments.length);
  let offset = 0;
  for (const s of segments) {
    assert.equal(s.start, offset);
    assert.equal(s.excerpt, text.slice(s.start, s.end));
    assert.equal(s.documentCharacters, text.length);
    assert.ok(s.excerpt.length <= EVIDENCE_CHUNK_CHARACTERS);
    offset = s.end;
  }
  assert.equal(offset, text.length);
});

test('short documents are complete, including facts beyond the old 900/1200 cutoffs', () => {
  const text = 'Heading\n' + 'a'.repeat(1350) + '\nWork did not proceed.';
  assert.equal(buildEvidenceSegments([doc(text)])[0].excerpt, text);
});

test('more than 32 segments remain searchable, with document-scoped identities', () => {
  const documents = Array.from({length: 35}, (_, i) => doc(`R3-EV-001 record ${i}`, `doc-${i}`));
  documents[34].extractedText += ' unique-tail-restoration';
  const segments = buildEvidenceSegments(documents);
  assert.equal(segments.length, 35);
  assert.equal(new Set(segments.map(s => s.sourceId)).size, 35);
  const found = retrieveForQuestion({text: 'unique-tail-restoration?', intent: '', evidenceNeeded: []}, documents, [], []);
  assert.equal(found[0].sourceId, 'doc-34#1');
});

test('retrieval searches document tails, not just the first representative section', () => {
  const text = 'unrelated '.repeat(900) + '\nTail-only-calibration was deferred.';
  const found = retrieveForQuestion({text: 'Tail-only-calibration?', intent: '', evidenceNeeded: []}, [doc(text)], [], []);
  assert.match(found[0].excerpt, /Tail-only-calibration was deferred/);
});

test('chunk boundaries preserve surrogate pairs and complete text', () => {
  const text = 'a'.repeat(2399) + '🔎' + 'b'.repeat(2400);
  const segments = buildEvidenceSegments([doc(text)]);
  assert.equal(segments.map(s => s.excerpt).join(''), text);
  for (const s of segments) assert.equal(s.excerpt.isWellFormed(), true);
});

test('initial understanding packet preserves full documents and answers without duplicate previews', () => {
  const text = 'z'.repeat(5000) + 'material qualification';
  const answer = {questionId: 'q', text: 'a'.repeat(13000) + 'final qualification'};
  const packet = evidencePacket({incident: 'Incident', documents: [doc(text)], answers: [answer]}, []);
  assert.equal(packet.evidenceSegments.map(s => s.excerpt).join(''), text);
  assert.equal(packet.answers[0].text, answer.text);
  assert.equal(packet.documents[0].extractedCharacters, text.length);
  assert.equal('preview' in packet.documents[0], false);
});

test('oversized stage packets stop explicitly and are not mutated', () => {
  const packet = {text: 'a'.repeat(MAX_STAGE_PACKET_CHARACTERS)};
  assert.throws(() => assertPacketFits('test', packet), /No evidence was truncated/);
  assert.equal(packet.text.length, MAX_STAGE_PACKET_CHARACTERS);
  assert.doesNotThrow(() => assertPacketFits('test', {text: 'small'}));
});

test('adjudication rejects schema capacity overflow before any provider call', async () => {
  const segments = buildEvidenceSegments(Array.from({length: 33}, (_, i) => doc('text', `d${i}`)));
  await assert.rejects(runEvidenceAdjudication({provider: 'ollama'}, {}, segments), /No segments were dropped/);
});

test('all relevant prompts preserve work-stage and uncertainty distinctions', () => {
  for (const stage of ['incident-understanding', 'incident-structuring', 'tagging', 'evidence-processing', 'causal-analysis', 'causal-verification']) {
    const prompt = promptFor(stage);
    assert.match(prompt, /pending acceptance.*does not establish unauthorized downstream work/);
    assert.match(prompt, /not proof of physical presence/);
    assert.match(prompt, /decision summaries must all preserve the same uncertainty/);
  }
  assert.match(promptFor('procedure-planning', 'procedure-planning'), /which work stage actually occurred/);
  assert.equal(PROMPT_VERSION, 'try4.2.5-lossless-claim-refs');
});
