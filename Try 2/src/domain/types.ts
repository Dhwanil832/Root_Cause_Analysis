export const TAGS = [
  'human',
  'electrical',
  'equipment-tool',
  'mobile-equipment',
  'crane-lifting',
  'stored-energy',
  'process-material',
  'work-environment',
  'procedure-planning',
  'communication-supervision',
  'maintenance-outage',
  'isolation-loto',
  'rail-locomotive',
  'animal-wildlife',
  'other-novel',
] as const;

export type TagId = (typeof TAGS)[number];

export interface TagResult {
  id: TagId;
  label: string;
  rationale: string;
  evidence: string[];
  confidence: number;
}

export interface InvestigationQuestion {
  id: string;
  tagId: TagId | 'baseline';
  text: string;
  intent: string;
  rationale: string;
  evidenceNeeded: string[];
  priority: 'high' | 'medium' | 'low';
  status: 'open' | 'answered' | 'screened';
}

export interface SkippedQuestion {
  id: string;
  proposedBy: TagId;
  text: string;
  intent: string;
  coveredByQuestionId: string;
  coveredByTagId: TagId | 'baseline';
  reason: string;
}

export interface TraceEntry {
  id: string;
  stage: 'baseline' | 'tagging' | 'specialists' | 'broker' | 'revision';
  summary: string;
  evidence: string[];
  unknowns: string[];
  confidence: number;
  promptVersion: string;
  engine: string;
  durationMs: number;
}

export interface InvestigationAnswer {
  questionId: string;
  text: string;
  fileName?: string;
  fileKey?: string;
  answeredAt: string;
}

export interface AnalysisSnapshot {
  facts: string[];
  unknowns: string[];
  baselineQuestions: InvestigationQuestion[];
  tags: TagResult[];
  questions: InvestigationQuestion[];
  skippedQuestions: SkippedQuestion[];
  trace: TraceEntry[];
  answers: InvestigationAnswer[];
}

export interface ModelDescriptor {
  id: string;
  name: string;
  provider: 'builtin' | 'ollama' | 'openai-compatible';
  detail: string;
  available: boolean;
}

export interface VersionRecord {
  id: string;
  number: number;
  createdAt: string;
  analysis: AnalysisSnapshot;
  trigger: string;
}

export interface TrackRecord {
  id: string;
  modelId: string;
  modelName: string;
  provider: string;
  versions: VersionRecord[];
}

export interface IncidentRecord {
  id: string;
  title: string;
  description: string;
  createdAt: string;
  updatedAt: string;
  tracks: TrackRecord[];
}
