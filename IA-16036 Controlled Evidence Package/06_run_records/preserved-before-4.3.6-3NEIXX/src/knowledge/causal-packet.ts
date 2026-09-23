import type { EvidenceClaim, InvestigationQuestion, SpecialistKnowledgeBase } from '@/src/domain/types';

type Packet = { evidenceClaims?: EvidenceClaim[]; specialistKnowledgeBases?: SpecialistKnowledgeBase[]; questions?: InvestigationQuestion[] };
function findingFor(claim: EvidenceClaim) {
  return { id: claim.id, statement: claim.text, type: claim.kind === 'inference' ? 'hypothesis' : 'finding',
    status: claim.status, sourceIds: claim.sourceIds };
}

/** Wire-only references: stored knowledge bases and the full claim ledger stay intact. */
export function compactCausalPacket(packet: unknown): unknown {
  if (!packet || typeof packet !== 'object') return packet;
  const value = packet as Packet;
  if (!Array.isArray(value.evidenceClaims) || !Array.isArray(value.specialistKnowledgeBases)) return packet;
  const claims = new Map(value.evidenceClaims.map(claim => [claim.id, claim]));
  // Ambiguous identities must never be compressed into a single reference.
  if (claims.size !== value.evidenceClaims.length) return packet;
  return { ...packet,
    ...(Array.isArray(value.questions) ? { questions: value.questions.map(question => ({
      ...question,
      ...(typeof question.intent === 'string' && question.causalBranch === question.intent ? {causalBranch:{sameAs:'intent'}} : {}),
      ...(typeof question.rationale === 'string' && question.decisionUnlocked === question.rationale ? {decisionUnlocked:{sameAs:'rationale'}} : {}),
    })) } : {}),
    specialistKnowledgeBases: value.specialistKnowledgeBases.map(kb => ({
    ...kb, findings: kb.findings.map(finding => {
      const claim = claims.get(finding.id);
      return claim && JSON.stringify(finding) === JSON.stringify(findingFor(claim))
        ? { claimRef: claim.id } : finding;
    }),
  })) };
}

/** Exact inverse for integrity tests and tools inspecting the wire representation. */
export function expandCausalPacket(packet: unknown): unknown {
  if (!packet || typeof packet !== 'object') return packet;
  const value = packet as Packet;
  if (!Array.isArray(value.evidenceClaims) || !Array.isArray(value.specialistKnowledgeBases)) return packet;
  const claims = new Map(value.evidenceClaims.map(claim => [claim.id, claim]));
  return { ...packet,
    ...(Array.isArray(value.questions) ? { questions: value.questions.map(question => {
      const restored = {...question};
      for (const [key, target] of [['causalBranch','intent'],['decisionUnlocked','rationale']] as const) {
        const field: unknown = question[key];
        if (field && typeof field === 'object') {
          if (Object.keys(field).length !== 1 || !('sameAs' in field) || field.sameAs !== target || typeof question[target] !== 'string') throw new Error('Invalid question field reference.');
          restored[key] = question[target];
        }
      }
      return restored;
    }) } : {}),
    specialistKnowledgeBases: value.specialistKnowledgeBases.map(kb => ({
    ...kb, findings: kb.findings.map(finding => {
      if (!('claimRef' in finding)) return finding;
      const claim = claims.get(String(finding.claimRef));
      if (!claim || Object.keys(finding).length !== 1) throw new Error('Invalid causal claim reference.');
      return findingFor(claim);
    }),
  })) };
}
