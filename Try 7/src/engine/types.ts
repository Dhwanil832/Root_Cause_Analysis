import type { AnalysisSnapshot, DocumentRecord, HumanDecision, InvestigationAnswer, ModelDescriptor, TagId } from '@/src/domain/types';
import type { ClaimReviewAssessment } from './review/decision';
import type { ClaimInterpretation } from './review/contract';

export const ENGINE_VERSION = 'try7.1.0';
export type TaskKind = 'read' | 'understand' | 'tag' | 'specialist' | 'broker' | 'answer' | 'interpret' | 'review' | 'causal' | 'inquiry' | 'verify' | 'actions' | 'frame' | 'consult' | 'resolve' | 'refine' | 'connect' | 'respond' | 'revise' | 'role';
export type TaskStatus = 'queued' | 'running' | 'completed' | 'failed' | 'blocked' | 'superseded';
export type RunStatus = 'queued' | 'running' | 'paused' | 'partial' | 'completed';
export type EpistemicStatus = 'proposed' | 'supported' | 'partial' | 'unknown' | 'contradicted' | 'conflicting';

export interface SourceSpan {
  id: string; sourceId: string; revision: string; label: string;
  scope: 'reference' | 'starter' | 'question' | 'incident' | 'answer';
  origin: 'document' | 'incident-account' | 'user-answer' | 'simulated-testimony';
  start: number; end: number; text: string; heading: string; tableHeader: string;
  modality?: 'image' | 'file';
}
export interface EngineSource {
  id: string; revision: string; label: string; textHash: string;
  scope: SourceSpan['scope']; origin: SourceSpan['origin']; spans: SourceSpan[];
  limitations: string[];
  questionId?: string;
}
export interface Finding {
  id: string; revision: number; statement: string;
  kind: 'observation' | 'measurement' | 'testimony' | 'requirement' | 'hypothesis' | 'context';
  subject: string; predicate: string; location: string; time: string; unit: string;
  qualifiers: string; spanIds: string[]; tags: TagId[]; owners: string[];
  status: EpistemicStatus; reviewReason: string; opposedBy: string[];
  history: Array<{ revision: number; statement: string; reason: string }>;
  introducedVersion: number; updatedVersion: number;
  humanStatus?: 'unreviewed' | 'accepted' | 'rejected' | 'reopened';
  causalRole?: 'event' | 'condition' | 'barrier' | 'requirement' | 'hypothesis' | 'context';
  causalRelevance?: string;
  reviewAssessment?: ClaimReviewAssessment;
  interpretation?: ClaimInterpretation;
  reviewExecution?: 'unreviewed' | 'complete' | 'incomplete';
  /** Classification history is not a truth verdict or an eligibility filter. */
  scopeHistory?: Array<{ revision: number; taskId: string; claimType: string }>;
}
export interface EngineQuestion {
  parts?: Array<{id:string;text:string}>;
  subscriptions?: Array<{id:string;owner:string;branchId?:string;targetIds:string[];decision:string;evidenceNeeded:string;ifPresent:string;ifAbsent:string;partIds:string[]}>;
  coverage?: Array<{partId:string;status:'answered'|'partial'|'conflicting'|'unavailable'|'not-found';answer:string;spanIds:string[];gap:string}>;
  answerRevision?: number;
  deliveries?: Array<{owner:string;answerRevision:number;status:'pending'|'received';taskId?:string;implication?:string}>;
  targetIds?: string[];
  id: string; text: string; intent: string; decision: string;
  subject: string; location: string; time: string; owners: string[]; spanIds: string[];
  status: 'open' | 'answered' | 'partial' | 'conflicting' | 'awaiting-user' | 'covered' | 'unavailable';
  answer: string; answerSpanIds: string[]; findingIds: string[]; coveredBy: string | null;
  reason: string; searchedSpanIds: string[]; inventory: string;
  answerCompleteness?: 'answered' | 'partial' | 'conflicting' | 'not-found' | 'unavailable';
  /** Claims whose proposed missing premises prompted this question. Not answers. */
  reviewTargets?: string[];
  inquiryTargets?: string[];
}
export interface Proposition {
  roleAssessment?: {status:'valid'|'invalid'|'unknown';role:string;reason:string;protectiveFunction:string;spanIds:string[];findingRevision:number;version:number};
  id: string; findingId: string; type: 'event' | 'condition' | 'barrier' | 'change' | 'human-decision-action';
  label: string; detail: string; spanIds: string[]; status: EpistemicStatus;
  reviewReason: string; humanStatus: 'unreviewed' | 'accepted' | 'rejected' | 'reopened';
  /** Retained for audit only; never part of the factual node or verification. */
  proposedWording?: { label: string; detail: string; taskId: string };
}
export interface Relationship {
  integrityIssues?: string[];
  jointConditions?: string[];
  id: string; from: string; to: string; type: 'caused' | 'enabled' | 'failed-to-prevent' | 'preceded' | 'combined-with';
  rationale: string; counterfactual: string; alternative: string; gap: string;
  spanIds: string[]; findingIds: string[]; status: EpistemicStatus; reviewReason: string;
  proposedBy?: string[];
}
export interface EngineTask {
  failureCategory?: 'harness'|'model-output'|'environment'|'evidence'|'unattributed';
  /** Execution completed with rejected individual proposals; not factual approval. */
  partial?: boolean;
  /** Revalidated saved output; not another inference attempt. Original trace retained. */
  formattingRecovery?: {policy:string;at:string;traceId:string;previousError:string};
  /** Actual executor version, retained across checkpoint migrations. */
  engineVersion?: string;
  targetRevision?: number;
  priority?: 'board';
  id: string; kind: TaskKind; owner: string; targetIds: string[];
  dependsOn: string[]; status: TaskStatus; attempts: number;
  query: string; requiredSpanIds: string[]; cacheKey: string;
  error: string; reused: boolean; output?: unknown;
  evidenceIds: string[]; omittedEvidenceIds: string[];
  contextBytes: number; durationMs: number; inputTokens: number; outputTokens: number;
  createdAt: string; completedAt?: string;
  traceId?: string;
  producedIds?: string[];
}
export interface EngineInput {
  release?: {id:string;trackId:string;parentVersion:number;hash:string;sourceIds:string[]};
  incident: string; model: Omit<ModelDescriptor, 'apiKey'>;
  answers: InvestigationAnswer[]; documents: DocumentRecord[];
  humanDecision?: HumanDecision; storyRoundId?: string;
  answerQuestions?: Record<string,string>;
  engineVersion?: string;
  reviewAfterReading?: boolean;
  /** Frozen formatting-only guardrail; absent on legacy runs. */
  reviewFormattingPolicy?: string;
}
export interface EngineState {
  investigation?: import('./investigation/types').InvestigationPosition;
  /** Explicit operator-approved migration; immutable source inputs stay intact. */
  executionMigrations?: Array<{from:string;to:string;at:string;reason:string;checkpointHash:string;backup?:string;recoveredTaskIds?:string[]}>;
  progressiveBoard?: boolean;
  reviewFormattingPolicy?: string;
  version: number; phase: number; initialized: boolean;
  reviewFormattingMigrations?: Array<{policy:string;at:string;reason:string;checkpointHash:string;backup:string;
    recoveredTaskIds:string[];retiredQuestionIds:string[]}>;
  sources: EngineSource[]; changedSourceIds: string[];
  findings: Finding[]; questions: EngineQuestion[];
  propositions: Proposition[]; relationships: Relationship[];
  tags: Array<{ id: TagId; reason: string; spanIds: string[] }>;
  summary: string; focalEvent: string; normalState: string; eventState: string;
  entities: Array<{ name: string; description: string; spanIds: string[] }>;
  tasks: EngineTask[]; quarantine: Array<{ taskId: string; reason: string; item: unknown }>;
  changes: Array<{ targetId: string; kind: 'added' | 'revised' | 'rechecked' | 'retained' | 'rejected'; reason: string; before?:string;after?:string;evidenceIds?:string[] }>;
  decisions: HumanDecision[]; actions: AnalysisSnapshot['correctiveActions'];
  followupPass?: boolean;
  pauseReason?: string;
  /** Operator-requested, single-task recovery; not an investigation-size limit. */
  pauseAfterTaskId?: string;
  readingApproved?: boolean;
  reviewAfterReading?: boolean;
  inquiries?: InquiryResult[];
}
export interface InquiryResult {
  id: string; taskId: string; findingIds: string[]; status: 'proposed'; summary: string;
  observations: Array<{ statement: string; spanIds: string[]; limitation: string }>;
  explanations: Array<{ id: string; title: string; mechanism: string; supportingSpanIds: string[]; opposingSpanIds: string[]; unresolved: string }>;
  questions: Array<{ questionId: string; evidenceNeeded: string; contrasts: Array<{ explanationId: string; expectedObservation: string; implication: string }> }>;
}
export interface EngineRun {
  id: string; trackId: string; number: number; parentNumber: number;
  status: RunStatus; trigger: string; input: EngineInput; state: EngineState | null;
  lease: string | null; leaseUntil: number; generation: number;
  createdAt: string; updatedAt: string;
  pauseReason?: string;
}
export interface CachedTask {
  key: string; trackId: string; kind: TaskKind; output: unknown;
  evidenceIds: string[]; createdAt: string;
}
export interface TaskExecutorResult {
  output: unknown; evidenceIds: string[]; omittedEvidenceIds: string[];
  contextBytes: number; durationMs: number; inputTokens: number; outputTokens: number;
  cacheKey: string; reused: boolean;
  providerAttempts?: unknown;
}
export interface EngineStore {
  claim(now: number, leaseMs: number): Promise<EngineRun | null>;
  renew(id: string, lease: string, until: number): Promise<boolean>;
  save(run: EngineRun, expectedGeneration: number, snapshot: AnalysisSnapshot, cache?: CachedTask): Promise<boolean>;
  previous(trackId: string, before: number): Promise<EngineState | null>;
  cached(trackId: string, key: string): Promise<CachedTask | null>;
  pause?(id: string, reason: string, lease?: string | null): Promise<boolean>;
  trace?(run: EngineRun, task: EngineTask): Promise<TaskTrace>;
}
export interface TaskTrace {
  request(value: unknown): Promise<void>;
  append(text: string): Promise<void>;
  complete(status: 'completed' | 'failed', result: unknown, error?: string): Promise<void>;
}
