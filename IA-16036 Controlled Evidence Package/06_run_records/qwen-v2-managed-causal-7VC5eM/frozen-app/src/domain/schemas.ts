import { z } from 'zod';
import { TAGS } from './types';

export const decisionSchema = z.object({
  summary: z.string(),
  evidenceUsed: z.array(z.string()).max(12),
  unknowns: z.array(z.string()).max(12),
  alternatives: z.array(z.string()).max(8),
  confidence: z.number().min(0).max(1),
});

export const questionCandidateSchema = z.object({
  intent: z.string(),
  text: z.string(),
  rationale: z.string(),
  evidenceNeeded: z.array(z.string()).min(1).max(8),
  priority: z.enum(['high', 'medium', 'low']),
  sourceIds: z.array(z.string()).max(12),
  routedTo: z.array(z.enum(TAGS)),
  causalBranch: z.string().optional(),
  decisionUnlocked: z.string().optional(),
});

export const understandingSchema = z.object({
  summary: z.string(),
  focalEvent: z.string(),
  actualImpact: z.string(),
  potentialImpact: z.string(),
  normalState: z.string(),
  eventState: z.string(),
  understoodFacts: z.array(z.string()),
  unknowns: z.array(z.string()),
  questions: z.array(questionCandidateSchema).max(8),
  decision: decisionSchema,
});

export const structuringSchema = z.object({
  entities: z.array(z.object({
    type: z.enum(['person', 'organization', 'equipment', 'component', 'location', 'material', 'energy', 'document', 'other']),
    name: z.string(),
    description: z.string(),
    status: z.enum(['proposed', 'supported', 'partially-supported', 'contradicted', 'rejected', 'verified', 'unknown']),
    sourceIds: z.array(z.string()),
  })),
  timeline: z.array(z.object({
    timeLabel: z.string(),
    sequence: z.number(),
    description: z.string(),
    kind: z.enum(['event', 'condition', 'decision', 'observation']),
    status: z.enum(['proposed', 'supported', 'partially-supported', 'contradicted', 'rejected', 'verified', 'unknown']),
    sourceIds: z.array(z.string()),
  })),
  conditions: z.array(z.string()),
  unknowns: z.array(z.string()),
  decision: decisionSchema,
});

export const taggingSchema = z.object({
  tags: z.array(z.object({
    id: z.enum(TAGS),
    rationale: z.string(),
    evidence: z.array(z.string()),
    unknowns: z.array(z.string()),
    confidence: z.number().min(0).max(1),
  })).max(10),
  decision: decisionSchema,
});

export const specialistSchema = z.object({
  summary: z.string(),
  findings: z.array(z.object({
    statement: z.string(),
    type: z.enum(['finding', 'hypothesis', 'unknown', 'screened-out']),
    status: z.enum(['proposed', 'supported', 'partially-supported', 'contradicted', 'rejected', 'verified', 'unknown']),
    sourceIds: z.array(z.string()),
    testNeeded: z.string().optional(),
  })).max(12),
  questions: z.array(questionCandidateSchema).max(8),
  handoffs: z.array(z.object({ tagId: z.enum(TAGS), reason: z.string() })),
  decision: decisionSchema,
});

export const brokerSchema = z.object({
  decisions: z.array(z.object({
    candidateKey: z.string(),
    disposition: z.enum(['keep', 'covered']),
    coveredByCandidateKey: z.string(),
    reason: z.string().min(1).max(500),
  })).min(1).max(4),
  decision: decisionSchema,
});

/** Constrain identifiers during decoding as well as validating their relations. */
export function brokerSchemaFor(candidateKeys: string[], catalogKeys: string[], answeredKeys: string[] = []) {
  if (!candidateKeys.length || candidateKeys.length > 4) throw new Error('Broker schema needs one bounded candidate batch.');
  const row = brokerSchema.shape.decisions.element;
  const alternatives: z.ZodType<z.infer<typeof row>>[] = [];
  for (const [index, candidateKey] of candidateKeys.entries()) {
    alternatives.push(row.extend({
      candidateKey: z.literal(candidateKey),
      disposition: z.literal('keep'),
      coveredByCandidateKey: z.literal(''),
    }));
    // Existing answers retain their question identity. For new questions, only
    // catalog entries and earlier candidates can possibly own coverage. Whether
    // that earlier candidate was kept remains a cross-row runtime invariant.
    const eligibleOwners = [...new Set([...catalogKeys, ...candidateKeys.slice(0, index)])]
      .filter(key => key !== candidateKey);
    if (!answeredKeys.includes(candidateKey) && eligibleOwners.length) alternatives.push(row.extend({
      candidateKey: z.literal(candidateKey),
      disposition: z.literal('covered'),
      coveredByCandidateKey: z.enum(eligibleOwners as [string, ...string[]]),
    }));
  }
  return brokerSchema.extend({
    decisions: z.array(alternatives.length === 1 ? alternatives[0] : z.union(alternatives)).length(candidateKeys.length),
  });
}

export const answerFetchSchema = z.object({
  status: z.enum(['answered', 'partial', 'conflicting', 'not-found']),
  answer: z.string(),
  sourceIds: z.array(z.string()),
  claims: z.array(z.object({
    text: z.string(),
    kind: z.enum(['direct-observation', 'testimony', 'record', 'measurement', 'documented-requirement', 'expert-interpretation', 'inference', 'assumption', 'hearsay']),
    status: z.enum(['proposed', 'supported', 'partially-supported', 'contradicted', 'rejected', 'verified', 'unknown']),
    sourceIds: z.array(z.string()),
    routedTo: z.array(z.enum(TAGS)),
  })).max(12),
  userRequest: z.string(),
  searched: z.array(z.string()),
  decision: decisionSchema,
});

export const evidenceAdjudicationSchema = z.object({
  assessments: z.array(z.object({
    sourceId: z.string(),
    documentId: z.string(),
    label: z.string().max(180),
    authority: z.enum(['controlled', 'official-record', 'first-hand', 'derived', 'uncontrolled', 'unknown']),
    directness: z.enum(['first-hand', 'contemporaneous-record', 'derived-summary', 'hearsay', 'unknown']),
    applicability: z.enum(['direct-incident', 'similar-equipment', 'general-guidance', 'unknown']),
    revisionStatus: z.enum(['current', 'superseded', 'uncontrolled', 'not-applicable', 'unknown']),
    reliability: z.enum(['high', 'medium', 'low', 'unusable']),
    supports: z.array(z.string().max(220)).max(3),
    cautions: z.array(z.string().max(220)).max(3),
    limitations: z.array(z.string().max(220)).max(3),
  })).max(32),
  conflicts: z.array(z.object({
    summary: z.string(),
    sourceIds: z.array(z.string()).min(2).max(8),
    resolutionNeeded: z.string(),
  })).max(20),
  decision: decisionSchema,
});

export const evidenceProcessingSchema = z.object({
  claims: z.array(z.object({
    text: z.string(),
    kind: z.enum(['direct-observation', 'testimony', 'record', 'measurement', 'documented-requirement', 'expert-interpretation', 'inference', 'assumption', 'hearsay']),
    status: z.enum(['proposed', 'supported', 'partially-supported', 'contradicted', 'rejected', 'verified', 'unknown']),
    sourceIds: z.array(z.string()),
    questionId: z.string(),
    routedTo: z.array(z.enum(TAGS)),
  })).max(40),
  conflicts: z.array(z.object({
    summary: z.string(),
    claimIndexes: z.array(z.number()),
    resolutionNeeded: z.string(),
  })).max(20),
  decision: decisionSchema,
});

export const documentIntelligenceSchema = z.object({
  documentType: z.string(),
  summary: z.string(),
  observations: z.array(z.object({
    text: z.string(),
    kind: z.enum(['transcribed-text', 'visual-feature', 'spatial-relationship', 'equipment-condition', 'document-structure', 'uncertainty']),
    location: z.string(),
    confidence: z.number().min(0).max(1),
    requiresVerification: z.boolean(),
    routedTo: z.array(z.enum(TAGS)),
  })).max(12),
  limitations: z.array(z.string()).max(8),
  decision: decisionSchema,
});

export const causalAnalysisSchema = z.object({
  maturity: z.enum(['initial', 'developing', 'ready-for-review', 'verified']),
  // The focal event is a required value, not a model-selected pointer. The
  // graph adapter assigns its reserved key and type without guessing a node.
  focalEvent: z.object({
    label: z.string().min(1),
    detail: z.string(),
    status: z.enum(['proposed', 'supported', 'partially-supported', 'contradicted', 'rejected', 'verified', 'unknown']),
    sourceIds: z.array(z.string()),
    specialistIds: z.array(z.enum(TAGS)),
  }).strict(),
  nodes: z.array(z.object({
    key: z.string().min(1),
    type: z.enum(['impact', 'event', 'condition', 'human-decision-action', 'barrier', 'change', 'direct-cause', 'contributing-cause', 'root-cause-candidate', 'corrective-action', 'evidence', 'unknown']),
    label: z.string(),
    detail: z.string(),
    status: z.enum(['proposed', 'supported', 'partially-supported', 'contradicted', 'rejected', 'verified', 'unknown']),
    sourceIds: z.array(z.string()),
    specialistIds: z.array(z.enum(TAGS)),
  })).max(17),
  edges: z.array(z.object({
    fromKey: z.string(),
    toKey: z.string(),
    type: z.enum(['caused', 'combined-with', 'preceded', 'enabled', 'failed-to-prevent', 'contradicted-by', 'supported-by', 'mitigated-by']),
    rationale: z.string(),
    status: z.enum(['proposed', 'supported', 'partially-supported', 'contradicted', 'rejected', 'verified', 'unknown']),
    sourceIds: z.array(z.string()),
    claimIds: z.array(z.string()).max(12),
    counterfactual: z.string(),
    competingExplanation: z.string(),
    evidenceGap: z.string(),
  })).max(24),
  questions: z.array(questionCandidateSchema).max(8),
  decision: decisionSchema,
}).strict();

export const verificationSchema = z.object({
  maturity: z.enum(['initial', 'developing', 'ready-for-review', 'verified']),
  verifiedNodeKeys: z.array(z.string()),
  verifiedEdgeIndexes: z.array(z.number()),
  findings: z.array(z.object({
    targetKey: z.string(),
    severity: z.enum(['blocking', 'important', 'advisory']),
    issue: z.string(),
    evidenceNeeded: z.string(),
    question: z.string(),
  })).max(16),
  decision: decisionSchema,
});

export const correctiveActionSchema = z.object({
  actions: z.array(z.object({
    title: z.string(),
    description: z.string(),
    type: z.enum(['containment', 'elimination', 'substitution', 'engineering', 'administrative', 'ppe']),
    causalTargetKeys: z.array(z.string()),
    ownerRole: z.string(),
    completionEvidence: z.string(),
    effectivenessCheck: z.string(),
  })),
  missingEvidence: z.array(z.string()),
  decision: decisionSchema,
});

export type UnderstandingOutput = z.infer<typeof understandingSchema>;
export type StructuringOutput = z.infer<typeof structuringSchema>;
export type TaggingOutput = z.infer<typeof taggingSchema>;
export type SpecialistOutput = z.infer<typeof specialistSchema>;
export type BrokerOutput = z.infer<typeof brokerSchema>;
export type AnswerFetchOutput = z.infer<typeof answerFetchSchema>;
export type EvidenceProcessingOutput = z.infer<typeof evidenceProcessingSchema>;
export type EvidenceAdjudicationOutput = z.infer<typeof evidenceAdjudicationSchema>;
export type DocumentIntelligenceOutput = z.infer<typeof documentIntelligenceSchema>;
export type CausalAnalysisOutput = z.infer<typeof causalAnalysisSchema>;
export type VerificationOutput = z.infer<typeof verificationSchema>;
export type CorrectiveActionOutput = z.infer<typeof correctiveActionSchema>;
