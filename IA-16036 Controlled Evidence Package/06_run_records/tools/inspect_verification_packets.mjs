// Inspect the real failed B0 input with the repaired packet planner. No model
// calls, synthetic fixtures, source changes or investigation-state writes.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { batchesBySize } from '../../../Try 4/src/knowledge/batches.ts';
import { buildEvidenceSegments } from '../../../Try 4/src/knowledge/evidence-segments.ts';
import { verificationPacketPartitions } from '../../../Try 4/src/stages/causal-verification/packet-partitions.ts';

const directory = path.resolve(process.argv[2]);
const input = JSON.parse(fs.readFileSync(path.join(directory, 'frozen-rca-input.json')));
const cp = JSON.parse(fs.readFileSync(path.join(directory, 'failure-snapshot.json'))).incident.tracks[0].checkpoints;
const last = stage => cp.findLast(c => c.stage === stage && c.status === 'completed' && !c.payload.kind).payload;
const board = last('causal-analysis').board;
const allClaims = last('claim-review').claims;
const saved = cp.filter(c => c.stage === 'causal-verification' && c.payload.kind === 'model-call').map(c => c.payload.requestIdentity.packet);
if (input.answers.length || input.previousVersion || saved.length !== 10) throw Error('Expected the failed initial B0 verification boundary');
const template = saved[0], segments = buildEvidenceSegments(input.documents), packets = [];
for (const targets of batchesBySize([...board.nodes, ...board.edges], 9_000, 3)) {
  const ids = new Set(targets.flatMap(t => t.sourceIds));
  const claimIds = new Set(targets.flatMap(t => 'claimIds' in t ? t.claimIds : []));
  const claims = allClaims.filter(c => claimIds.has(c.id) || c.sourceIds.some(id => ids.has(id)));
  for (const claim of claims) for (const id of claim.sourceIds) ids.add(id);
  const pages = batchesBySize(segments.filter(s => ids.has(s.sourceId) || ids.has(s.documentId)), 18_000, 8);
  for (const page of pages.length ? pages : [[]]) packets.push({
    originalIncident: template.originalIncident, answers: template.answers,
    sources: page, claims, conflicts: template.conflicts, targets,
    nodes: board.nodes.filter(n => targets.some(t => t.id === n.id || ('from' in t && (t.from === n.id || t.to === n.id)))),
    sourcePages: Math.max(1, pages.length),
  });
}
saved.forEach((packet, index) => assert.equal(JSON.stringify(packet), JSON.stringify(packets[index])));
const planned = packets.map(verificationPacketPartitions);
for (const [index, parts] of planned.entries()) {
  const original = packets[index];
  for (const part of parts) {
    assert.ok(JSON.stringify(part).length <= 60_000);
    for (const field of ['targets', 'nodes', 'originalIncident', 'sourcePages']) assert.deepEqual(part[field], original[field]);
  }
  for (const field of ['claims', 'sources', 'answers', 'conflicts']) {
    const union = new Set(parts.flatMap(p => p[field].map(item => JSON.stringify(item))));
    assert.deepEqual(union, new Set(original[field].map(item => JSON.stringify(item))));
  }
  if (JSON.stringify(original).length <= 60_000) assert.deepEqual(parts, [original]);
}
const flat = planned.flat();
saved.forEach((packet, index) => assert.equal(JSON.stringify(packet), JSON.stringify(flat[index])));
console.log(JSON.stringify({ inspectedAt: new Date().toISOString(), originalPackets: packets.length,
  plannedPackets: flat.length, exactReusableVerificationCalls: saved.length,
  allOriginalContextRecordsPreserved: true, allTargetsPreservedOnEveryPartition: true,
  largestPlannedPacket: Math.max(...flat.map(p => JSON.stringify(p).length)),
  changedPackets: planned.flatMap((parts, index) => parts.length > 1 ? [{ index: index + 1,
    originalCharacters: JSON.stringify(packets[index]).length,
    originalClaimCharacters: JSON.stringify(packets[index].claims).length,
    partitionCharacters: parts.map(p => JSON.stringify(p).length),
    originalClaims: packets[index].claims.length, claimsPerPartition: parts.map(p => p.claims.length),
  }] : []),
}, null, 2));
