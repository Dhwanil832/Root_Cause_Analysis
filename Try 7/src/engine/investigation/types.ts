import type { TagId } from '@/src/domain/types';

/** Hypotheses are deliberately separate from source findings and verified nodes. */
export interface InvestigationBranch {
  applicability?:string;
  assumptions?:string[];
  conditions?:Array<{id:string;statement:string;status:'established'|'contradicted'|'unknown'|'conflicting';findings:string[];expectedObservation:string;scope:string}>;
  alternatives?:string[];
  distinguishes?:Array<{observation:string;ifEstablished:string;ifRuledOut:string}>;
  replaces?:string[];
  id: string;
  title: string;
  mechanism: string;
  status: 'open' | 'disfavored' | 'unresolved' | 'withdrawn' | 'superseded';
  supporting: string[];
  opposing: string[];
  gap: string;
  changeReason: string;
  updatedVersion: number;
}
export interface Consultation {
  id: string;
  branchId: string;
  domain: TagId;
  purpose: string;
  findingIds: string[];
  fingerprint: string;
  summary: string;
  limitations: string;
  completedVersion?: number;
}
export interface EvidenceDirection {
  questionId: string;
  branchIds: string[];
  evidenceNeeded: string;
  ifPresent: string;
  ifAbsent: string;
  priority: 'discriminating' | 'foundation';
}
export interface InvestigationPosition {
  proposedNarrative?:{summary:string;reason:string;taskId:string};
  revisionPass?:string;
  settleStarted?:boolean;
  lateResolutionStarted?:boolean;
  impacts?:Array<{targetId:string;action:string;reason:string;findingIds:string[];version:number;taskId:string}>;
  pendingImpacts?:string[];
  nodeRequests?: Array<{findingId:string;reason:string;taskId:string;version:number}>;
  rejectedConnections?: Array<{taskId:string;fromFindingId:string;toFindingId:string;rationale:string;reason:string}>;
  policy: 'investigation-led-v1';
  stage: string;
  ready: boolean;
  selectedFindingIds: string[];
  branches: InvestigationBranch[];
  consultations: Consultation[];
  directions: EvidenceDirection[];
  readSpanIds: string[];
  readingNotes: Array<{ text: string; taskId: string }>;
  priorQuestionIds: string[];
  priorBranchIds: string[];
  changedFindingIds: string[];
  summary: string;
  revisionReason: string;
}

export function emptyPosition(): InvestigationPosition {
  return { policy: 'investigation-led-v1', stage: 'Reading new evidence', ready: false,
    selectedFindingIds: [], branches: [], consultations: [], directions: [], readSpanIds: [],
    readingNotes: [], priorQuestionIds: [], priorBranchIds: [], changedFindingIds: [], summary: '', revisionReason: '' };
}
