export const TAGS = [
  'human', 'electrical', 'equipment-tool', 'mobile-equipment', 'crane-lifting',
  'stored-energy', 'process-material', 'work-environment', 'procedure-planning',
  'communication-supervision', 'maintenance-outage', 'isolation-loto',
  'rail-locomotive', 'animal-wildlife', 'other-novel',
] as const;

export type TagId = (typeof TAGS)[number];
export type AgentId = TagId | 'incident-understanding' | 'incident-structuring' |
  'tagging' | 'question-broker' | 'answer-fetching' | 'document-intelligence' | 'evidence-processing' |
  'evidence-adjudication' | 'claim-review' | 'evidence-reading' | 'causal-analysis' | 'causal-verification' | 'corrective-actions' | 'revision';
export type EvidenceStatus = 'proposed' | 'supported' | 'partially-supported' |
  'contradicted' | 'rejected' | 'verified' | 'unknown';
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
    'answered' | 'covered' | 'contradicted' | 'screened' | 'superseded' | 'reopened';
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
  review?: { verdict: 'supported' | 'partial' | 'unsupported' | 'contradicted'; reason: string; citations: Citation[] };
  proposedStatus?: EvidenceStatus;
}

export interface EvidenceConflict {
  id: string;
  summary: string;
  claimIds: string[];
  status: 'open' | 'resolved';
  resolutionNeeded: string;
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
  status: 'answered' | 'partial' | 'conflicting' | 'not-found';
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
  id: string;
  type: CausalNodeType;
  label: string;
  detail: string;
  status: EvidenceStatus;
  sourceIds: string[];
  specialistIds: TagId[];
  verified: boolean;
  proposedStatus?: EvidenceStatus;
}

export interface CausalEdge {
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

export interface CausalBoard {
  maturity: 'initial' | 'developing' | 'ready-for-review' | 'verified';
  focalNodeId: string;
  nodes: CausalNode[];
  edges: CausalEdge[];
  verificationFindings: VerificationFinding[];
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
