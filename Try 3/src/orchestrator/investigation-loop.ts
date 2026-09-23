import type {
  AnalysisSnapshot,
  DocumentRecord,
  EvidenceClaim,
  InvestigationAnswer,
  InvestigationQuestion,
  ModelDescriptor,
  SpecialistKnowledgeBase,
  StageError,
  TraceEntry,
} from '@/src/domain/types';
import { PROMPT_VERSION } from '@/src/prompts/manifest';
import { runAnswerFetchers } from '@/src/stages/answer-fetching/run';
import { runCausalAnalysis } from '@/src/stages/causal-analysis/run';
import { runCausalVerification } from '@/src/stages/causal-verification/run';
import { runCorrectiveActions } from '@/src/stages/corrective-actions/run';
import { runEvidenceProcessing } from '@/src/stages/evidence-processing/run';
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
      text: document.extractedText.slice(0, 18_000),
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
          causalBoard: input.previous.causalBoard,
          conflicts: input.previous.conflicts,
        }
      : null,
  };
}

function failureTrace(stage: TraceEntry['stage'], error: Error): TraceEntry {
  return {
    id: crypto.randomUUID(),
    stage,
    summary: 'This stage failed validation, so the inspectable fallback remained in use.',
    evidence: [],
    unknowns: [error.message],
    alternatives: ['Retry this model', 'Compare another model track', 'Continue with fallback output'],
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
  const fail = (stage: TraceEntry['stage'], caught: unknown) => {
    const error = caught instanceof Error ? caught : new Error('Unknown stage failure.');
    stageErrors.push({ stage, message: error.message, recoverable: true });
    trace.push(failureTrace(stage, error));
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
      fail('document-intelligence', new Error(`${failure.documentId}: ${failure.error.message}`));
    }
    const extractionTrace = documentIntelligenceTrace(documentIntelligence);
    if (extractionTrace) trace.push(extractionTrace);
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

  let understanding: Awaited<ReturnType<typeof runIncidentUnderstanding>> | null = null;
  try {
    understanding = await runIncidentUnderstanding(input.model, packet, answers);
    trace.push(understanding.trace);
  } catch (error) {
    fail('incident-understanding', error);
  }

  let structured = fallback.structuredIncident;
  if (understanding) {
    try {
      const result = await runIncidentStructuring(input.model, packet, understanding.output);
      structured = result.structured;
      trace.push(result.trace);
    } catch (error) {
      fail('incident-structuring', error);
    }
  }

  let tags = fallback.tags;
  try {
    const result = await runTagging(input.model, packet, structured);
    tags = result.tags;
    trace.push(result.trace);
  } catch (error) {
    fail('tagging', error);
  }

  const specialistQuestions: InvestigationQuestion[] = [];
  const knowledgeBases: SpecialistKnowledgeBase[] = [];
  try {
    const result = await runSpecialists(
      input.model,
      { packet, structuredIncident: structured },
      tags,
      answers,
      input.previous?.specialistKnowledgeBases || [],
    );
    for (const success of result.successes) {
      specialistQuestions.push(...success.questions);
      knowledgeBases.push(success.knowledgeBase);
      trace.push(success.result.trace);
    }
    for (const failure of result.failures) {
      fail(failure.tag.id, failure.error);
      const prior = fallback.specialistKnowledgeBases.find((kb) => kb.tagId === failure.tag.id);
      if (prior) knowledgeBases.push(prior);
      specialistQuestions.push(...fallback.questions.filter((question) => question.tagId === failure.tag.id));
    }
  } catch (error) {
    fail(tags[0]?.id || 'other-novel', error);
    knowledgeBases.push(...fallback.specialistKnowledgeBases);
    specialistQuestions.push(...fallback.questions);
  }

  const baselineQuestions = understanding?.questions || fallback.baselineQuestions;
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
  } catch (error) {
    fail('question-broker', error);
    const brokered = deterministicBroker([...baselineQuestions, ...specialistQuestions]);
    questions = brokered.questions;
    skippedQuestions = brokered.skipped;
  }

  const answeredIds = new Set(answers.filter((answer) => answer.text.trim()).map((answer) => answer.questionId));
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
    for (const failure of result.failures) fail('answer-fetching', failure.error);
  } catch (error) {
    fail('answer-fetching', error);
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

  let processedClaims = fallback.evidenceClaims;
  let conflicts = fallback.conflicts;
  try {
    const result = await runEvidenceProcessing(
      input.model,
      { structuredIncident: structured },
      answers,
      documents,
      input.previous?.evidenceClaims || [],
    );
    processedClaims = result.claims;
    conflicts = result.conflicts;
    trace.push(result.trace);
  } catch (error) {
    fail('evidence-processing', error);
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

  let causalBoard = fallback.causalBoard;
  let causalQuestions: InvestigationQuestion[] = [];
  let keyToId = new Map<string, string>();
  try {
    const result = await runCausalAnalysis(input.model, {
      structuredIncident: structured,
      specialistKnowledgeBases: knowledgeBases,
      evidenceClaims,
      conflicts,
      questions,
      previousBoard: input.previous?.causalBoard || null,
    });
    causalBoard = result.board;
    causalQuestions = result.questions;
    keyToId = result.keyToId;
    trace.push(result.trace);
  } catch (error) {
    fail('causal-analysis', error);
  }

  let verificationQuestions: InvestigationQuestion[] = [];
  try {
    const result = await runCausalVerification(input.model, { evidenceClaims, conflicts }, causalBoard, keyToId);
    causalBoard = result.board;
    verificationQuestions = result.questions;
    trace.push(result.trace);
  } catch (error) {
    fail('causal-verification', error);
  }

  if (causalQuestions.length || verificationQuestions.length) {
    const finalBroker = deterministicBroker([...questions, ...causalQuestions, ...verificationQuestions]);
    questions = finalBroker.questions;
    skippedQuestions = [...skippedQuestions, ...finalBroker.skipped];
  }

  let correctiveActions = fallback.correctiveActions;
  try {
    const result = await runCorrectiveActions(
      input.model,
      { causalBoard, verificationFindings: causalBoard.verificationFindings },
      keyToId,
    );
    correctiveActions = result.actions;
    trace.push(result.trace);
  } catch (error) {
    fail('corrective-actions', error);
  }

  const unknowns = [...new Set([
    ...structured.unknowns,
    ...questions
      .filter((question) => !['answered', 'screened', 'superseded'].includes(question.status))
      .map((question) => question.text),
    ...conflicts.map((conflict) => conflict.resolutionNeeded),
  ])];
  const status: AnalysisSnapshot['status'] = conflicts.some((conflict) => conflict.status === 'open')
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
