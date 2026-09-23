import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const root = new URL('../', import.meta.url);
const read = path => JSON.parse(readFileSync(new URL(path, root), 'utf8'));
const meta = read('src/history/featured-comparison.json');
const saved = read('public/history/featured-causal-boards.json');

test('pinned incident contains both boards and matching history metadata', () => {
  assert.deepEqual(saved.metadata, meta);
  assert.deepEqual(saved.versions.map(v => v.number), [1, 2]);
  for (const [index, version] of saved.versions.entries()) {
    assert.equal(version.board.nodes.length, meta.versions[index].nodes);
    assert.equal(version.board.edges.length, meta.versions[index].edges);
    assert.ok(version.board.nodes.length > 0);
  }
});

test('every saved board is identical to its original output and source file hash', () => {
  for (const version of saved.versions) {
    const bytes = readFileSync(new URL('../' + version.sourcePath, root));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), version.sourceSha256);
    const source = JSON.parse(bytes);
    const original = source.analysis?.causalBoard || source.causalBoard || source.runs?.find(r => r.version === version.number)?.board;
    assert.ok(original, 'Original board must be present');
    assert.deepEqual(version.board, original);
  }
});

test('diagnostic snapshots are not represented as published application versions', () => {
  if (meta.kind === 'controlled-revision') {
    assert.match(meta.note, /operator-frozen partial checkpoint/);
    assert.match(meta.note, /selected-answers-v1/);
    assert.equal(meta.originalIncidentId, 'e99d24d6-753c-427a-9304-cdbd6726090f');
    assert.equal(saved.versions[0].status, 'partial');
    assert.match(saved.versions[0].label, /Frozen partial/);
  } else if (meta.app === 'Try 5') {
    assert.equal(meta.kind, 'diagnostic-snapshots');
    assert.match(meta.note, /NOT published application versions/);
    assert.ok(saved.versions.every(v => /Diagnostic snapshot/.test(v.label)));
  } else {
    assert.equal(meta.kind, 'published-versions');
  }
});

test('archive precedes other history cards and uses read-only version-specific canvases', () => {
  const history = readFileSync(new URL('app/history/page.tsx', root), 'utf8');
  assert.ok(history.indexOf('<FeaturedComparisonCard />') < history.indexOf('{items.map'));
  const page = readFileSync(new URL('app/history/causal-comparison/page.tsx', root), 'utf8');
  assert.match(page, /readOnly/);
  assert.match(page, /originalTrackId}:v\$\{v.number\}/);
  const canvas = readFileSync(new URL('app/incident/causal-canvas.tsx', root), 'utf8');
  assert.match(canvas, /if \(provisional \|\| readOnly\) return;/);
  assert.match(canvas, /!provisional && !readOnly && REVIEWABLE/);
});
