export const TAGS = [
  'human', 'electrical', 'equipment-tool', 'mobile-equipment', 'crane-lifting',
  'stored-energy', 'process-material', 'work-environment', 'procedure-planning',
  'communication-supervision', 'maintenance-outage', 'isolation-loto',
  'rail-locomotive', 'animal-wildlife', 'other-novel',
] as const;

export type TagId = (typeof TAGS)[number];
export type AgentId = TagId | 'incident-understanding' | 'incident-structuring' |
  'tagging' | 'question-broker' | 'answer-fetching' | 'document-intelligence' | 'evidence-processing' |
  'evidence-adjudication' | 'claim-interpretation' | 'claim-review' | 'evidence-reading' | 'causal-analysis' | 'causal-verification' | 'corrective-actions' | 'revision';
export type EvidenceStatus = 'proposed' | 'supported' | 'partially-supported' |
  'contradicted' | 'rejected' | 'verified' | 'unknown' | 'conflicting';
export type DocumentScope = 'reference' | 'starter' | 'question';

export interface Citation {
  sourceId: string;
  label: string;
  excerpt: string;
}

export interface TagResult {
  id: TagId;
  label: string;
  rationale: string;
  evidence: string[];
  citations?: Citation[];
  unknowns?: string[];
  confidence: number;
}

export interface InvestigationQuestion {
  parts?: Array<{id:string;text:string}>;
  coverage?:Array<{partId:string;status:string;answer:string;spanIds:string[];gap:string}>;
  subscriptions?:Array<{owner:string;branchId?:string;decision:string;evidenceNeeded:string;ifPresent:string;ifAbsent:string;partIds:string[]}>;
  deliveries?:Array<{owner:string;answerRevision:number;status:string;implication?:string}>;
  searchStatus?:'not-yet-searched'|'searched';
  id: string;
  tagId: TagId | 'baseline' | 'causal-analysis' | 'causal-verification';
  proposedBy?: AgentId;
  routedTo?: TagId[];
  text: string;
  intent: string;
  rationale: string;
  evidenceNeeded: string[];
  causalBranch?: string;
  decisionUnlocked?: string;
  citations?: Citation[];
  priority: 'high' | 'medium' | 'low';
  status: 'proposed' | 'open' | 'searching' | 'awaiting-user' | 'partially-answered' |
    'answered' | 'covered' | 'contradicted' | 'screened' | 'superseded' | 'reopened' | 'conflicting' | 'unavailable';
}

export interface SkippedQuestion {
  id: string;
  proposedBy: TagId | 'baseline' | 'causal-analysis' | 'causal-verification';
  text: string;
  intent: string;
  coveredByQuestionId: string;
  coveredByTagId: TagId | 'baseline' | 'causal-analysis' | 'causal-verification';
  reason: string;
}

export interface InvestigationAnswer {
  questionId: string;
  text: string;
  sourceId?: string;
  fileName?: string;
  fileKey?: string;
  answeredAt: string;
  responseStatus?: 'answered' | 'partial' | 'unknown' | 'unavailable';
}

export interface IncidentEntity {
  id: string;
  type: 'person' | 'organization' | 'equipment' | 'component' | 'location' |
    'material' | 'energy' | 'document' | 'other';
  name: string;
  description: string;
  status: EvidenceStatus;
  sourceIds: string[];
}

export interface TimelineEvent {
  id: string;
  timeLabel: string;
  sequence: number;
  description: string;
  kind: 'event' | 'condition' | 'decision' | 'observation';
  status: EvidenceStatus;
  sourceIds: string[];
}

export interface StructuredIncident {
  summary: string;
  focalEvent: string;
  actualImpact: string;
  potentialImpact: string;
  normalState: string;
  eventState: string;
  entities: IncidentEntity[];
  timeline: TimelineEvent[];
  conditions: string[];
  unknowns: string[];
}

export interface EvidenceClaim {
  id: string;
  text: string;
  kind: 'direct-observation' | 'testimony' | 'record' | 'measurement' |
    'documented-requirement' | 'expert-interpretation' | 'inference' |
    'assumption' | 'hearsay';
  status: EvidenceStatus;
  sourceIds: string[];
  questionId?: string;
  routedTo: TagId[];
  interpretation?: {policy:string;targetStatement:string;parts:Array<{partId:string;claimText:string;claimType:string;assertion:string;truthConditions:string;scope:{subject:string;location:string;time:string};ambiguities:string[]}>};
  reviewExecution?: 'unreviewed' | 'complete' | 'incomplete';
  scopeHistory?: Array<{revision:number;taskId:string;claimType:string}>;
  review?: { verdict: 'supported' | 'partial' | 'unsupported' | 'contradicted'; reason: string; citations: Citation[];
    assessments?: Array<{ proposedVerdict: string; effectiveVerdict: string; checks: Record<string, boolean>; issues: string[] }>;
    claimParts?: { policy: string; status: string; uncoveredText: string[]; issues: string[];
      parts: Array<{ claimText: string; claimType: string; assertion?:string; truthConditions?:string; establishes: string; relation: string; status: string;
        reason: string; missingPremises: string[]; issues: string[]; citations: Citation[];
        counterexample?: {possible:boolean;scenario:string};
        originalQuotes: Array<{ source: string; line:number; quote: string; claimText?:string;label?:string;revision?:string;localRef?:string }> }> } };
  proposedStatus?: EvidenceStatus;
}

export interface EvidenceConflict {
  id: string;
  summary: string;
  claimIds: string[];
  status: 'open' | 'resolved';
  resolutionNeeded: string;
  scope?: {subject:string;location:string;time:string};
  sides?: Array<{assertion:string;citations:Citation[];originalQuotes:Array<{source:string;line:number;quote:string;label?:string;revision?:string;localRef?:string}>}>;
}

export interface EvidenceSourceAssessment {
  id: string;
  sourceId: string;
  documentId: string;
  label: string;
  authority: 'controlled' | 'official-record' | 'first-hand' | 'derived' | 'uncontrolled' | 'unknown';
  directness: 'first-hand' | 'contemporaneous-record' | 'derived-summary' | 'hearsay' | 'unknown';
  applicability: 'direct-incident' | 'direct-r3' | 'similar-equipment' | 'general-guidance' | 'unknown';
  revisionStatus: 'current' | 'superseded' | 'uncontrolled' | 'not-applicable' | 'unknown';
  reliability: 'high' | 'medium' | 'low' | 'unusable';
  supports: string[];
  cautions: string[];
  limitations: string[];
}

export interface EvidenceAdjudicationConflict {
  id: string;
  summary: string;
  sourceIds: string[];
  resolutionNeeded: string;
}

export interface SpecialistFinding {
  id: string;
  statement: string;
  type: 'finding' | 'hypothesis' | 'unknown' | 'screened-out';
  status: EvidenceStatus;
  sourceIds: string[];
  testNeeded?: string;
}

export interface SpecialistKnowledgeBase {
  tagId: TagId;
  label: string;
  summary: string;
  findings: SpecialistFinding[];
  questionIds: string[];
  handoffs: Array<{ tagId: TagId; reason: string }>;
  updatedAt: string;
}

export interface AnswerFetchResult {
  id: string;
  questionId: string;
  status: 'answered' | 'partial' | 'conflicting' | 'not-found' | 'unavailable' | 'not-yet-searched';
  answer: string;
  sourceIds: string[];
  claimIds: string[];
  userRequest: string;
  searched: string[];
}

export type CausalNodeType = 'focal-event' | 'impact' | 'event' | 'condition' |
  'human-decision-action' | 'barrier' | 'change' | 'direct-cause' |
  'contributing-cause' | 'root-cause-candidate' | 'corrective-action' |
  'evidence' | 'unknown';

export interface CausalNode {
  roleStatus?:'valid'|'invalid'|'unknown'|'not-assessed';
  roleReason?:string;
  humanStatus?: 'unreviewed' | 'accepted' | 'rejected' | 'reopened';
  id: string;
  type: CausalNodeType;
  label: string;
  detail: string;
  status: EvidenceStatus;
  sourceIds: string[];
  specialistIds: TagId[];
  verified: boolean;
  proposedStatus?: EvidenceStatus;
  claimIds?: string[];
  assessmentKind?: 'observation' | 'hypothesis';
}

export interface CausalEdge {
  jointConditions?:string[];
  id: string;
  from: string;
  to: string;
  type: 'caused' | 'combined-with' | 'preceded' | 'enabled' |
    'failed-to-prevent' | 'contradicted-by' | 'supported-by' | 'mitigated-by';
  rationale: string;
  status: EvidenceStatus;
  sourceIds: string[];
  claimIds: string[];
  counterfactual: string;
  competingExplanation: string;
  evidenceGap: string;
  verified: boolean;
  proposedStatus?: EvidenceStatus;
}

export interface VerificationFinding {
  id: string;
  targetId: string;
  severity: 'blocking' | 'important' | 'advisory';
  issue: string;
  evidenceNeeded: string;
  question?: string;
}

/** A rejected model proposal is not an active causal relationship. */
export interface RejectedCausalEdge {
  id: string;
  fromLabel: string;
  toLabel: string;
  reasons: string[];
  proposal: Pick<CausalEdge, 'type' | 'rationale' | 'status' | 'sourceIds' | 'claimIds' |
    'counterfactual' | 'competingExplanation' | 'evidenceGap'> & { fromKey: string; toKey: string };
}

export interface CausalBoard {
  maturity: 'initial' | 'developing' | 'ready-for-review' | 'verified';
  focalNodeId: string;
  nodes: CausalNode[];
  edges: CausalEdge[];
  verificationFindings: VerificationFinding[];
  rejectedEdges?: RejectedCausalEdge[];
  proposalLedger?: Array<{ candidateId: string; originalLabel: string;
    disposition: 'board' | 'merge' | 'context' | 'question' | 'rejected';
    reason: string; canonicalId: string | null; question: string }>;
  branchRevisions?: Array<{ previousTargetId: string; previousLabel: string;
    action: 'keep' | 'strengthen' | 'weaken' | 'revise' | 'reject' | 'unresolved';
    reason: string; replacementIds: string[]; evidenceIds: string[] }>;
}

export interface CorrectiveAction {
  id: string;
  title: string;
  description: string;
  type: 'containment' | 'elimination' | 'substitution' | 'engineering' |
    'administrative' | 'ppe';
  causalTargetIds: string[];
  ownerRole: string;
  completionEvidence: string;
  effectivenessCheck: string;
  status: 'proposed' | 'accepted' | 'in-progress' | 'implemented' | 'verified';
}

export interface HumanDecision {
  id: string;
  targetType: 'causal-node' | 'causal-branch' | 'corrective-action' | 'document-observation';
  targetId: string;
  action: 'accept' | 'reject' | 'close-branch' | 'approve';
  notes: string;
  actor: string;
  createdAt: string;
}

export interface TraceEntry {
  id: string;
  stage: AgentId;
  summary: string;
  evidence: string[];
  unknowns: string[];
  alternatives: string[];
  confidence: number;
  promptVersion: string;
  engine: string;
  durationMs: number;
  validation: 'valid' | 'repaired' | 'fallback' | 'failed';
  reused?: boolean;
}

export interface StageError {
  stage: AgentId;
  message: string;
  recoverable: boolean;
}

export interface DocumentRecord {
  visibility?: 'released' | 'controller-only' | 'future';
  id: string;
  scope: DocumentScope;
  title: string;
  fileName: string;
  fileKey: string;
  contentType: string;
  size: number;
  sha256: string;
  revision: string;
  plant: string;
  incidentId?: string;
  trackId?: string;
  questionId?: string;
  introducedVersion?: number;
  extractionStatus: 'ready' | 'partial' | 'unsupported' | 'failed';
  extractionNotes: string;
  extractedText: string;
  createdAt: string;
}

export type DocumentObservationKind = 'transcribed-text' | 'visual-feature' |
  'spatial-relationship' | 'equipment-condition' | 'document-structure' | 'uncertainty';

export interface DocumentObservation {
  id: string;
  documentId: string;
  text: string;
  kind: DocumentObservationKind;
  location: string;
  confidence: number;
  status: EvidenceStatus;
  requiresVerification: boolean;
  routedTo: TagId[];
}

export interface DocumentIntelligenceRecord {
  documentId: string;
  title: string;
  fileName: string;
  contentType: string;
  mode: 'embedded-text' | 'vision' | 'file-vision' | 'unavailable';
  documentType: string;
  summary: string;
  observations: DocumentObservation[];
  limitations: string[];
  processedAt: string;
  engine: string;
  validation: 'valid' | 'repaired' | 'fallback' | 'failed';
}

export interface RevisionSummary {
  added: string[];
  changed: string[];
  resolved: string[];
  reopened: string[];
}

export interface AnalysisSnapshot {
  investigationPosition?: {
    proposedNarrative?:{summary:string;reason:string;taskId:string};
    impacts?:Array<{targetId:string;action:string;reason:string;findingIds:string[];version:number;taskId:string}>;
    pendingImpacts?:string[];
    stage: string; ready: boolean; summary: string; revisionReason: string;
    notebookCount: number; selectedCount: number; reusedSourceSpans: number;
    branches: Array<{ id: string; title: string; mechanism: string; status: string; gap: string; changeReason: string;
      supporting: string[]; opposing: string[];applicability?:string;assumptions?:string[];
      conditions?:Array<{id:string;statement:string;status:string;expectedObservation:string;scope:string}>;
      distinguishes?:Array<{observation:string;ifEstablished:string;ifRuledOut:string}> }>;
    directions: Array<{ questionId: string; question: string; branchIds: string[]; evidenceNeeded: string; ifPresent: string; ifAbsent: string; priority: string; status: string }>;
    consultations: Array<{ id: string; domain: string; branchId: string; purpose: string; summary: string; limitations: string; completedVersion?: number }>;
  };
  engineProgress?: {
    assessmentGate?: {status:'pending'|'execution-inconclusive'|'ready-for-output-review';issues:string[]};
    status: 'queued' | 'running' | 'paused' | 'partial' | 'completed'; phase: number; quarantineCount: number; pauseReason?:string;
    model?: {id:string;digest?:string;contextWindow?:number;engineVersion:string};
    tasks: Array<{ id: string; kind: string; owner: string; status: string; attempts: number; error: string; reused: boolean;
      target?:string;decision?:string;dependencies?:number;traceId?:string;failureCategory?:string;
      inputTokens: number; outputTokens: number; durationMs: number; contextBytes: number; evidenceCount: number; omittedEvidenceCount: number }>;
    changes: Array<{ targetId: string; kind: string; reason: string;before?:string;after?:string;evidenceIds?:string[] }>;
      sourceCoverage: Array<{ id: string; label: string; spans: number; limitations: string[];readSpans?:number }>;
      quarantine?:Array<{taskId:string;reason:string}>;
  };
  status: 'initial-fact-gathering' | 'active-specialist-investigation' |
    'awaiting-evidence' | 'contradictions-unresolved' | 'causal-board-developing' |
    'ready-for-human-review' | 'root-causes-accepted' |
    'corrective-actions-proposed' | 'closed';
  structuredIncident: StructuredIncident;
  facts: string[];
  unknowns: string[];
  baselineQuestions: InvestigationQuestion[];
  tags: TagResult[];
  specialistKnowledgeBases: SpecialistKnowledgeBase[];
  questions: InvestigationQuestion[];
  skippedQuestions: SkippedQuestion[];
  answers: InvestigationAnswer[];
  documentIntelligence: DocumentIntelligenceRecord[];
  sourceAssessments: EvidenceSourceAssessment[];
  adjudicationConflicts: EvidenceAdjudicationConflict[];
  evidenceClaims: EvidenceClaim[];
  conflicts: EvidenceConflict[];
  answerFetches: AnswerFetchResult[];
  causalBoard: CausalBoard;
  correctiveActions: CorrectiveAction[];
  humanDecisions: HumanDecision[];
  trace: TraceEntry[];
  stageErrors: StageError[];
  revision: RevisionSummary;
  documentIds: string[];
}

export interface StageCheckpointRecord {
  id: string;
  trackId: string;
  runId: string;
  targetVersion: number;
  sequence: number;
  stage: AgentId;
  status: 'completed' | 'failed' | 'blocked';
  payload: unknown;
  createdAt: string;
}

export interface ModelDescriptor {
  id: string;
  name: string;
  provider: 'builtin' | 'ollama' | 'openai-compatible';
  detail: string;
  available: boolean;
  providerConfigId?: string;
  baseUrl?: string;
  apiKey?: string;
  apiMode?: 'responses' | 'chat-completions';
  capabilities?: string[];
  digest?: string;
  /** Native model window when reported; absent means provider-managed, not unlimited. */
  contextWindow?: number;
}

export interface ProviderConfig {
  id: string;
  name: string;
  baseUrl: string;
  apiMode: 'responses' | 'chat-completions';
  modelIds: string[];
  keyHint: string;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface VersionRecord {
  executionStatus?: 'queued' | 'running' | 'paused' | 'partial' | 'completed';
  id: string;
  number: number;
  trigger: string;
  createdAt: string;
  analysis: AnalysisSnapshot;
}

export interface TrackRecord {
  id: string;
  modelId: string;
  modelName: string;
  provider: string;
  versions: VersionRecord[];
  documents: DocumentRecord[];
  checkpoints?: StageCheckpointRecord[];
}

export interface IncidentRecord {
  id: string;
  title: string;
  description: string;
  createdAt: string;
  updatedAt: string;
  starterDocuments: DocumentRecord[];
  tracks: TrackRecord[];
}
