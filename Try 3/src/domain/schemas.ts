import { z } from 'zod';
import { TAGS } from './types';

export const decisionSchema = z.object({
  summary: z.string(),
  evidenceUsed: z.array(z.string()),
  unknowns: z.array(z.string()),
  alternatives: z.array(z.string()),
  confidence: z.number().min(0).max(1),
});

export const questionCandidateSchema = z.object({
  intent: z.string(),
  text: z.string(),
  rationale: z.string(),
  evidenceNeeded: z.array(z.string()),
  priority: z.enum(['high', 'medium', 'low']),
  sourceIds: z.array(z.string()),
  routedTo: z.array(z.enum(TAGS)),
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
  questions: z.array(questionCandidateSchema),
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
  })),
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
  })),
  questions: z.array(questionCandidateSchema),
  handoffs: z.array(z.object({ tagId: z.enum(TAGS), reason: z.string() })),
  decision: decisionSchema,
});

export const brokerSchema = z.object({
  canonical: z.array(z.object({
    candidateKey: z.string(),
    text: z.string(),
    intent: z.string(),
    rationale: z.string(),
    evidenceNeeded: z.array(z.string()),
    priority: z.enum(['high', 'medium', 'low']),
    routedTo: z.array(z.enum(TAGS)),
  })),
  covered: z.array(z.object({
    candidateKey: z.string(),
    coveredByCandidateKey: z.string(),
    reason: z.string(),
  })),
  decision: decisionSchema,
});

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
  })),
  userRequest: z.string(),
  searched: z.array(z.string()),
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
  })),
  conflicts: z.array(z.object({
    summary: z.string(),
    claimIndexes: z.array(z.number()),
    resolutionNeeded: z.string(),
  })),
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
  focalKey: z.string(),
  nodes: z.array(z.object({
    key: z.string(),
    type: z.enum(['focal-event', 'impact', 'event', 'condition', 'human-decision-action', 'barrier', 'change', 'direct-cause', 'contributing-cause', 'root-cause-candidate', 'corrective-action', 'evidence', 'unknown']),
    label: z.string(),
    detail: z.string(),
    status: z.enum(['proposed', 'supported', 'partially-supported', 'contradicted', 'rejected', 'verified', 'unknown']),
    sourceIds: z.array(z.string()),
    specialistIds: z.array(z.enum(TAGS)),
  })),
  edges: z.array(z.object({
    fromKey: z.string(),
    toKey: z.string(),
    type: z.enum(['caused', 'combined-with', 'preceded', 'enabled', 'failed-to-prevent', 'contradicted-by', 'supported-by', 'mitigated-by']),
    rationale: z.string(),
    status: z.enum(['proposed', 'supported', 'partially-supported', 'contradicted', 'rejected', 'verified', 'unknown']),
    sourceIds: z.array(z.string()),
  })),
  questions: z.array(questionCandidateSchema),
  decision: decisionSchema,
});

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
  })),
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
export type DocumentIntelligenceOutput = z.infer<typeof documentIntelligenceSchema>;
export type CausalAnalysisOutput = z.infer<typeof causalAnalysisSchema>;
export type VerificationOutput = z.infer<typeof verificationSchema>;
export type CorrectiveActionOutput = z.infer<typeof correctiveActionSchema>;
