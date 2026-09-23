import type {
  AnalysisSnapshot,
  AgentId,
  CausalBoard,
  DocumentRecord,
  EvidenceAdjudicationConflict,
  EvidenceClaim,
  EvidenceSourceAssessment,
  InvestigationAnswer,
  InvestigationQuestion,
  ModelDescriptor,
  SpecialistKnowledgeBase,
  StageError,
  TraceEntry,
} from '@/src/domain/types';
import { stableId } from '@/src/domain/ids';
import { buildEvidenceSegments } from '@/src/knowledge/evidence-segments';
import { PROMPT_VERSION } from '@/src/prompts/manifest';
import { runAnswerFetchers } from '@/src/stages/answer-fetching/run';
import { runCausalAnalysis } from '@/src/stages/causal-analysis/run';
import { previousBoardContext } from '@/src/stages/causal-analysis/label-contract';
import { runCausalVerification } from '@/src/stages/causal-verification/run';
import { runCorrectiveActions } from '@/src/stages/corrective-actions/run';
import { runEvidenceProcessing } from '@/src/stages/evidence-processing/run';
import { runEvidenceAdjudication } from '@/src/stages/evidence-adjudication/run';
import {
  baselineDocumentIntelligence,
  documentIntelligenceTrace,
  documentObservationClaims,
  runDocumentIntelligence,
} from '@/src/stages/document-intelligence/run';
import { runIncidentStructuring } from '@/src/stages/incident-structuring/run';
import { runIncidentUnderstanding } from '@/src/stages/incident-understanding/run';
import { deterministicBroker, runQuestionBroker } from '@/src/stages/question-broker/run';
import { runSpecialists } from '@/src/stages/specialists/run';
import { runTagging } from '@/src/stages/tagging/run';
import { runDeterministicAnalysis } from './deterministic-engine';
import type { ModelMedia } from '@/src/providers/types';

export interface InvestigationCycleInput {
  incident: string;
  model: ModelDescriptor;
  answers?: InvestigationAnswer[];
  documents?: DocumentRecord[];
  previous?: AnalysisSnapshot;
  documentMedia?: ModelMedia[];
  strictExecution?: boolean;
  onCheckpoint?: (checkpoint: {
    stage: AgentId;
    status: 'completed' | 'failed' | 'blocked';
    payload: unknown;
  }) => Promise<void>;
}

function evidencePacket(input: InvestigationCycleInput, documentIntelligence: AnalysisSnapshot['documentIntelligence']) {
  return {
    originalIncident: { sourceId: 'incident-description', text: input.incident },
    answers: (input.answers || []).map((answer) => ({ ...answer, text: answer.text.slice(0, 12_000) })),
    documents: (input.documents || []).map((document) => ({
      id: document.id,
      scope: document.scope,
      title: document.title,
      fileName: document.fileName,
      revision: document.revision,
      sha256: document.sha256,
      extractionStatus: document.extractionStatus,
      extractionNotes: document.extractionNotes,
      preview: document.extractedText.slice(0, 1_200),
    })),
    documentIntelligence: documentIntelligence.map((record) => ({
      documentId: record.documentId,
      mode: record.mode,
      documentType: record.documentType,
      summary: record.summary,
      observations: record.observations,
      limitations: record.limitations,
    })),
    previousVersion: input.previous
      ? {
          status: input.previous.status,
          facts: input.previous.facts,
          unknowns: input.previous.unknowns,
          openQuestions: [...input.previous.baselineQuestions, ...input.previous.questions].filter(
            (question) => !['answered', 'screened', 'superseded'].includes(question.status),
          ),
          specialistKnowledgeBases: input.previous.specialistKnowledgeBases,
          causalBoard: previousBoardContext(input.previous.causalBoard),
          conflicts: input.previous.conflicts,
        }
      : null,
  };
}

function minimalCausalBoard(structured: AnalysisSnapshot['structuredIncident'], reason: string): CausalBoard {
  const focalId = stableId('node', `focal:${structured.focalEvent}`);
  return {
    maturity: 'initial',
    focalNodeId: focalId,
    nodes: [{
      id: focalId,
      type: 'focal-event',
      label: structured.focalEvent.slice(0, 150),
      detail: structured.focalEvent,
      status: 'supported',
      sourceIds: ['incident-description'],
      specialistIds: [],
      verified: false,
    }],
    edges: [],
    verificationFindings: [{
      id: stableId('verify', `causal-stage:${reason}`),
      targetId: focalId,
      severity: 'blocking',
      issue: reason,
      evidenceNeeded: 'A valid model-produced causal analysis with cited forward causal links.',
    }],
  };
}

function failureTrace(stage: TraceEntry['stage'], error: Error): TraceEntry {
  return {
    id: crypto.randomUUID(),
    stage,
    summary: 'This model stage failed validation. No model-derived fallback content was substituted.',
    evidence: [],
    unknowns: [error.message],
    alternatives: ['Review the saved stage checkpoint', 'Retry this same model after correcting the contract'],
    confidence: 0,
    promptVersion: PROMPT_VERSION,
    engine: 'harness',
    durationMs: 0,
    validation: 'failed',
  };
}

function mergeClaims(...sets: EvidenceClaim[][]) {
  const claims = new Map<string, EvidenceClaim>();
  for (const claim of sets.flat()) claims.set(claim.id, claim);
  return [...claims.values()];
}

export async function runInvestigationCycle(input: InvestigationCycleInput): Promise<AnalysisSnapshot> {
  const answers = input.answers || [];
  const documents = input.documents || [];
  const trace: TraceEntry[] = [];
  const stageErrors: StageError[] = [];
  const recordedFailures = new WeakSet<Error>();
  const checkpoint = async (stage: AgentId, status: 'completed' | 'failed' | 'blocked', payload: unknown) => {
    await input.onCheckpoint?.({ stage, status, payload });
  };
  const fail = async (stage: TraceEntry['stage'], caught: unknown) => {
    const error = caught instanceof Error ? caught : new Error('Unknown stage failure.');
    if (recordedFailures.has(error)) throw error;
    recordedFailures.add(error);
    stageErrors.push({ stage, message: error.message, recoverable: true });
    trace.push(failureTrace(stage, error));
    await checkpoint(stage, 'failed', {
      error: error.message, providerAttempts: (caught as { attempts?: unknown })?.attempts,
      brokerBatches: (caught as { brokerBatches?: unknown })?.brokerBatches,
    });
    if (input.strictExecution) throw error;
  };

  let documentIntelligence = baselineDocumentIntelligence(
    documents,
    input.previous?.documentIntelligence || [],
  );
  if (input.model.provider !== 'builtin') {
    const result = await runDocumentIntelligence(
      input.model,
      input.incident,
      documents,
      input.documentMedia || [],
      input.previous?.documentIntelligence || [],
    );
    documentIntelligence = result.records;
    trace.push(...result.traces);
    for (const failure of result.failures) {
      await fail('document-intelligence', new Error(`${failure.documentId}: ${failure.error.message}`));
    }
    const extractionTrace = documentIntelligenceTrace(documentIntelligence);
    if (extractionTrace) trace.push(extractionTrace);
    await checkpoint('document-intelligence', 'completed', { records: documentIntelligence, failures: result.failures.length });
  }

  const fallback = runDeterministicAnalysis(
    input.incident,
    input.model,
    answers,
    documents,
    input.previous,
    documentIntelligence,
  );
  if (input.model.provider === 'builtin') return fallback;

  const packet = evidencePacket(input, documentIntelligence);
  const evidenceSegments = buildEvidenceSegments(documents);

  let understanding: Awaited<ReturnType<typeof runIncidentUnderstanding>> | null = null;
  try {
    understanding = await runIncidentUnderstanding(input.model, packet, answers);
    trace.push(understanding.trace);
    await checkpoint('incident-understanding', 'completed', understanding.output);
  } catch (error) {
    await fail('incident-understanding', error);
  }

  let structured = fallback.structuredIncident;
  if (understanding) {
    try {
      const result = await runIncidentStructuring(input.model, packet, understanding.output);
      structured = result.structured;
      trace.push(result.trace);
      await checkpoint('incident-structuring', 'completed', structured);
    } catch (error) {
      await fail('incident-structuring', error);
    }
  }

  let tags: AnalysisSnapshot['tags'] = [];
  try {
    const result = await runTagging(input.model, {
      originalIncident: packet.originalIncident,
      answers: packet.answers,
      previousVersion: packet.previousVersion,
    }, structured);
    tags = result.tags;
    trace.push(result.trace);
    await checkpoint('tagging', 'completed', tags);
  } catch (error) {
    await fail('tagging', error);
  }

  let sourceAssessments: EvidenceSourceAssessment[] = input.previous?.sourceAssessments || [];
  let adjudicationConflicts: EvidenceAdjudicationConflict[] = input.previous?.adjudicationConflicts || [];
  try {
    const result = await runEvidenceAdjudication(
      input.model,
      { structuredIncident: structured, tags, previousAssessments: sourceAssessments },
      evidenceSegments,
    );
    sourceAssessments = result.assessments;
    adjudicationConflicts = result.conflicts;
    trace.push(result.trace);
    await checkpoint('evidence-adjudication', 'completed', { sourceAssessments, adjudicationConflicts });
  } catch (error) {
    await fail('evidence-adjudication', error);
  }

  const specialistQuestions: InvestigationQuestion[] = [];
  const knowledgeBases: SpecialistKnowledgeBase[] = [];
  try {
    const result = await runSpecialists(
      input.model,
      { structuredIncident: structured, sourceAssessments, adjudicationConflicts },
      tags,
      answers,
      input.previous?.specialistKnowledgeBases || [],
    );
    for (const success of result.successes) {
      specialistQuestions.push(...success.questions);
      knowledgeBases.push(success.knowledgeBase);
      trace.push(success.result.trace);
      await checkpoint(success.knowledgeBase.tagId, 'completed', {
        knowledgeBase: success.knowledgeBase,
        questions: success.questions,
      });
    }
    for (const failure of result.failures) {
      await fail(failure.tag.id, failure.error);
      const prior = input.previous?.specialistKnowledgeBases.find((kb) => kb.tagId === failure.tag.id);
      if (prior) knowledgeBases.push(prior);
    }
  } catch (error) {
    await fail(tags[0]?.id || 'other-novel', error);
    knowledgeBases.push(...(input.previous?.specialistKnowledgeBases || []));
  }

  const baselineQuestions = understanding?.questions || [];
  let questions: InvestigationQuestion[];
  let skippedQuestions;
  try {
    const result = await runQuestionBroker(
      input.model,
      { structuredIncident: structured },
      [...baselineQuestions, ...specialistQuestions],
    );
    questions = result.questions;
    skippedQuestions = result.skipped;
    trace.push(result.trace);
    await checkpoint('question-broker', 'completed', { questions, skippedQuestions, batches: result.batches });
  } catch (error) {
    await fail('question-broker', error);
    const brokered = deterministicBroker([...baselineQuestions, ...specialistQuestions]);
    questions = brokered.questions;
    skippedQuestions = brokered.skipped;
  }

  const answeredIds = new Set(answers.filter((answer) => answer.text.trim() && (!answer.responseStatus || answer.responseStatus === 'answered')).map((answer) => answer.questionId));
  questions = questions.map((question) =>
    answeredIds.has(question.id) ? { ...question, status: 'answered' as const } : question,
  );

  const answerFetches = [];
  let fetchedClaims: EvidenceClaim[] = [];
  try {
    const result = await runAnswerFetchers(input.model, { structuredIncident: structured }, questions, documents, answers, knowledgeBases);
    for (const success of result.successes) {
      answerFetches.push(success.fetch);
      fetchedClaims = fetchedClaims.concat(success.claims);
      if (success.trace) trace.push(success.trace);
    }
    for (const failure of result.failures) await fail('answer-fetching', failure.error);
    await checkpoint('answer-fetching', 'completed', { answerFetches, fetchedClaims });
  } catch (error) {
    await fail('answer-fetching', error);
  }

  const fetchedByQuestion = new Map(answerFetches.map((fetch) => [fetch.questionId, fetch]));
  questions = questions.map((question) => {
    if (answeredIds.has(question.id)) return { ...question, status: 'answered' as const };
    const fetched = fetchedByQuestion.get(question.id);
    if (!fetched) return question;
    const status = fetched.status === 'answered' ? 'answered'
      : fetched.status === 'partial' ? 'partially-answered'
      : fetched.status === 'conflicting' ? 'contradicted'
      : 'awaiting-user';
    return { ...question, status };
  });

  let processedClaims: EvidenceClaim[] = [];
  let conflicts = input.previous?.conflicts || [];
  try {
    const result = await runEvidenceProcessing(
      input.model,
      { structuredIncident: structured, adjudicationConflicts },
      answers,
      evidenceSegments,
      sourceAssessments,
      input.previous?.evidenceClaims || [],
    );
    processedClaims = result.claims;
    conflicts = result.conflicts;
    trace.push(result.trace);
    await checkpoint('evidence-processing', 'completed', { claims: processedClaims, conflicts });
  } catch (error) {
    await fail('evidence-processing', error);
  }
  const evidenceClaims = mergeClaims(
    input.previous?.evidenceClaims || [],
    processedClaims,
    fetchedClaims,
    documentObservationClaims(documentIntelligence),
  );

  for (const knowledgeBase of knowledgeBases) {
    for (const claim of evidenceClaims.filter((item) => item.routedTo.includes(knowledgeBase.tagId))) {
      if (knowledgeBase.findings.some((finding) => finding.id === claim.id)) continue;
      knowledgeBase.findings.push({
        id: claim.id,
        statement: claim.text,
        type: claim.kind === 'inference' ? 'hypothesis' : 'finding',
        status: claim.status,
        sourceIds: claim.sourceIds,
      });
    }
  }

  let causalBoard = minimalCausalBoard(structured, 'The model has not yet produced a valid causal analysis.');
  let causalQuestions: InvestigationQuestion[] = [];
  let keyToId = new Map<string, string>();
  try {
    const result = await runCausalAnalysis(input.model, {
      structuredIncident: structured,
      specialistKnowledgeBases: knowledgeBases,
      evidenceClaims,
      conflicts,
      sourceAssessments,
      adjudicationConflicts,
      questions,
      previousBoard: previousBoardContext(input.previous?.causalBoard),
    });
    causalBoard = result.board;
    causalQuestions = result.questions;
    keyToId = result.keyToId;
    trace.push(result.trace);
    await checkpoint('causal-analysis', 'completed', {
      board: causalBoard, questions: causalQuestions,
      rawModelOutput: result.output, labelCorrections: result.labelCorrections,
      providerAttempts: result.providerAttempts,
    });
  } catch (error) {
    await fail('causal-analysis', error);
    causalBoard = minimalCausalBoard(structured, `Causal-analysis stage failed: ${error instanceof Error ? error.message : 'unknown error'}`);
  }

  let verificationQuestions: InvestigationQuestion[] = [];
  if (keyToId.size) {
    try {
      const result = await runCausalVerification(
        input.model,
        { evidenceClaims, conflicts, sourceAssessments, adjudicationConflicts },
        causalBoard,
        keyToId,
      );
      causalBoard = result.board;
      verificationQuestions = result.questions;
      trace.push(result.trace);
      await checkpoint('causal-verification', 'completed', { board: causalBoard, questions: verificationQuestions });
    } catch (error) {
      await fail('causal-verification', error);
    }
  } else {
    await checkpoint('causal-verification', 'blocked', { reason: 'No valid model-produced causal board was available.' });
  }

  if (causalQuestions.length || verificationQuestions.length) {
    const finalBroker = deterministicBroker([...questions, ...causalQuestions, ...verificationQuestions]);
    questions = finalBroker.questions;
    skippedQuestions = [...skippedQuestions, ...finalBroker.skipped];
  }

  let correctiveActions: AnalysisSnapshot['correctiveActions'] = [];
  const eligibleCausalTargets = causalBoard.nodes.filter((node) =>
    node.verified
    && ['supported', 'verified'].includes(node.status)
    && ['barrier', 'direct-cause', 'contributing-cause', 'root-cause-candidate'].includes(node.type),
  );
  if (['ready-for-review', 'verified'].includes(causalBoard.maturity) && eligibleCausalTargets.length) {
    try {
      const result = await runCorrectiveActions(
        input.model,
        { causalBoard, eligibleCausalTargets, verificationFindings: causalBoard.verificationFindings },
        keyToId,
      );
      correctiveActions = result.actions;
      trace.push(result.trace);
      await checkpoint('corrective-actions', 'completed', correctiveActions);
    } catch (error) {
      await fail('corrective-actions', error);
    }
  } else {
    await checkpoint('corrective-actions', 'blocked', {
      reason: 'Corrective actions require at least one verified causal target on a review-ready board.',
    });
  }

  const unknowns = [...new Set([
    ...structured.unknowns,
    ...questions
      .filter((question) => !['answered', 'screened', 'superseded'].includes(question.status))
      .map((question) => question.text),
    ...conflicts.map((conflict) => conflict.resolutionNeeded),
    ...adjudicationConflicts.map((conflict) => conflict.resolutionNeeded),
  ])];
  const status: AnalysisSnapshot['status'] = conflicts.some((conflict) => conflict.status === 'open') || adjudicationConflicts.length > 0
    ? 'contradictions-unresolved'
    : ['ready-for-review', 'verified'].includes(causalBoard.maturity)
      ? correctiveActions.length ? 'corrective-actions-proposed' : 'ready-for-human-review'
      : questions.some((question) => question.status === 'awaiting-user')
        ? 'awaiting-evidence'
        : 'causal-board-developing';

  return {
    status,
    structuredIncident: structured,
    facts: understanding?.output.understoodFacts || fallback.facts,
    unknowns,
    baselineQuestions,
    tags,
    specialistKnowledgeBases: knowledgeBases,
    questions: questions.filter((question) => question.tagId !== 'baseline'),
    skippedQuestions,
    answers,
    documentIntelligence,
    sourceAssessments,
    adjudicationConflicts,
    evidenceClaims,
    conflicts,
    answerFetches,
    causalBoard,
    correctiveActions,
    humanDecisions: input.previous?.humanDecisions || [],
    trace,
    stageErrors,
    revision: input.previous
      ? {
          added: evidenceClaims
            .filter((claim) => !input.previous?.evidenceClaims.some((old) => old.id === claim.id))
            .map((claim) => claim.text),
          changed: ['Tags, specialist knowledge, questions, and causal board re-evaluated'],
          resolved: input.previous.conflicts
            .filter((old) => !conflicts.some((current) => current.id === old.id))
            .map((conflict) => conflict.summary),
          reopened: [],
        }
      : { added: ['Initial investigation created'], changed: [], resolved: [], reopened: [] },
    documentIds: documents.map((document) => document.id),
  };
}
