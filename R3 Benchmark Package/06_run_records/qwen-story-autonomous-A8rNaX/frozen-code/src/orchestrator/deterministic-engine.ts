import { QUESTION_CATALOG, TAG_KEYWORDS, TAG_LABELS } from '@/src/domain/tag-catalog';
import { stableId } from '@/src/domain/ids';
import type {
  AnalysisSnapshot, CausalNode, DocumentRecord, EvidenceClaim, InvestigationAnswer,
  InvestigationQuestion, ModelDescriptor, SpecialistKnowledgeBase, TagId, TagResult, TraceEntry,
  DocumentIntelligenceRecord,
} from '@/src/domain/types';
import { deterministicBroker } from '@/src/stages/question-broker/run';
import { PROMPT_VERSION } from '@/src/prompts/manifest';
import { documentObservationClaims } from '@/src/stages/document-intelligence/run';

function sentences(text: string) {
  return text.split(/(?<=[.!?])\s+/).map((item) => item.trim()).filter(Boolean);
}

function containsKeyword(text: string, keyword: string) {
  const escaped = keyword.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&');
  return new RegExp(`(^|[^a-z0-9])${escaped}([^a-z0-9]|$)`, 'i').test(text);
}

function selectTags(text: string): TagResult[] {
  const selected: TagResult[] = [];
  for (const [id, keywords] of Object.entries(TAG_KEYWORDS) as Array<[TagId, string[]]>) {
    if (id === 'other-novel') continue;
    const hits = keywords.filter((keyword) => containsKeyword(text, keyword));
    if (!hits.length) continue;
    selected.push({
      id, label: TAG_LABELS[id],
      rationale: `The evidence directly references ${hits.slice(0, 4).join(', ')}, making this a material specialist direction.`,
      evidence: sentences(text).filter((sentence) => hits.some((hit) => containsKeyword(sentence, hit))).slice(0, 3),
      unknowns: [], confidence: Math.min(0.95, 0.58 + hits.length * 0.06),
    });
  }
  return selected;
}

function trace(stage: TraceEntry['stage'], summary: string, evidence: string[], unknowns: string[], confidence = 0.78): TraceEntry {
  return {
    id: crypto.randomUUID(), stage, summary, evidence, unknowns, alternatives: [], confidence,
    promptVersion: PROMPT_VERSION, engine: 'builtin:inspectable-preview', durationMs: 1, validation: 'fallback',
  };
}

function baselineQuestions(text: string, answers: InvestigationAnswer[]): InvestigationQuestion[] {
  const result: InvestigationQuestion[] = [];
  const technicalTerms = [...text.matchAll(/(?:\b[A-Z][A-Za-z0-9-]*\s+){0,4}\b(?:Beam|Yoke|Pit|Mill|System|Stand|Balance|Carrier|Cylinder)\b/g)]
    .map((match) => match[0].trim());
  if (technicalTerms.length) {
    result.push({
      id: stableId('bq', 'site-vocabulary'), tagId: 'baseline', proposedBy: 'incident-understanding', routedTo: ['equipment-tool'],
      text: `In this site and process, what are ${[...new Set(technicalTerms)].slice(0, 6).join(', ')}, and how do they normally relate?`,
      intent: 'site-vocabulary', rationale: 'The account uses site-specific terminology whose function cannot safely be assumed.',
      evidenceNeeded: ['annotated layout', 'equipment drawing', 'plain-language subject-matter explanation'], priority: 'high', status: 'open',
    });
  }
  result.push({
    id: stableId('bq', 'normal-vs-event'), tagId: 'baseline', proposedBy: 'incident-understanding', routedTo: ['equipment-tool', 'procedure-planning'],
    text: 'What was the normal operating or work configuration, and exactly what was different at the incident time?',
    intent: 'normal-vs-event', rationale: 'Change analysis requires a reliable normal-state baseline.',
    evidenceNeeded: ['normal arrangement drawing', 'procedure', 'event-time configuration record'], priority: 'high', status: 'open',
  });
  if (/previous shift|prior|morning|outage|turn\s+\d/i.test(text)) {
    result.push({
      id: stableId('bq', 'event-timeline'), tagId: 'baseline', proposedBy: 'incident-understanding', routedTo: ['communication-supervision'],
      text: 'What is the verified timeline from the last known normal condition through the event, including earlier shifts, crews, and contractors?',
      intent: 'event-timeline', rationale: 'Multiple times or work groups may hide a consequential state change.',
      evidenceNeeded: ['shift logs', 'work orders', 'witness chronology', 'control or access records'], priority: 'high', status: 'open',
    });
  }
  return result.map((question) => ({
    ...question,
    status: answers.some((answer) => answer.questionId === question.id && answer.text.trim()) ? 'answered' : question.status,
  }));
}

export function runDeterministicAnalysis(
  incident: string,
  model: ModelDescriptor,
  answers: InvestigationAnswer[] = [],
  documents: DocumentRecord[] = [],
  previous?: AnalysisSnapshot,
  documentIntelligence: DocumentIntelligenceRecord[] = [],
): AnalysisSnapshot {
  const sourceText = [incident, ...answers.map((answer) => answer.text), ...documents.map((document) => document.extractedText)].join('\n');
  const facts = sentences(incident).slice(0, 12);
  const tags = selectTags(sourceText);
  const baseline = baselineQuestions(incident, answers);
  const specialistKnowledgeBases: SpecialistKnowledgeBase[] = tags.map((tag) => ({
    tagId: tag.id, label: tag.label,
    summary: `${tag.label} remains an active investigation lens. The preview engine has opened evidence requests without declaring a cause.`,
    findings: [{ id: stableId('finding', `${tag.id}:${tag.rationale}`), statement: tag.rationale, type: 'finding', status: 'supported', sourceIds: ['incident-description'] }],
    questionIds: QUESTION_CATALOG[tag.id].map((candidate) => stableId('q', `${tag.id}:${candidate.intent}`)),
    handoffs: [], updatedAt: new Date().toISOString(),
  }));
  const specialistQuestions = tags.flatMap((tag) => QUESTION_CATALOG[tag.id].map((candidate): InvestigationQuestion => {
    const id = stableId('q', `${tag.id}:${candidate.intent}`);
    return {
      id, tagId: tag.id, proposedBy: tag.id, routedTo: [tag.id], text: candidate.text,
      intent: candidate.intent, rationale: candidate.rationale, evidenceNeeded: candidate.evidence,
      priority: ['energy-state', 'release-sequence', 'physical-condition', 'work-scope'].includes(candidate.intent) ? 'high' : 'medium',
      status: answers.some((answer) => answer.questionId === id && answer.text.trim()) ? 'answered' : 'proposed',
    };
  }));
  const brokered = deterministicBroker([...baseline, ...specialistQuestions]);
  const answerByQuestion = new Map(answers.map((answer) => [answer.questionId, answer]));
  const questions = brokered.questions.map((question) => ({
    ...question,
    status: answerByQuestion.has(question.id) ? 'answered' as const : documents.length ? 'awaiting-user' as const : 'open' as const,
  }));
  const evidenceClaims: EvidenceClaim[] = [
    ...facts.map((fact, index) => ({
      id: stableId('claim', `incident:${index}:${fact}`), text: fact, kind: 'record' as const,
      status: 'supported' as const, sourceIds: ['incident-description'], routedTo: [] as TagId[],
    })),
    ...answers.map((answer) => ({
      id: stableId('claim', `answer:${answer.questionId}:${answer.text}`), text: answer.text,
      kind: 'testimony' as const, status: 'supported' as const,
      sourceIds: [answer.sourceId || `answer:${answer.questionId}`], questionId: answer.questionId,
      routedTo: questions.find((question) => question.id === answer.questionId)?.routedTo || [],
    })),
    ...documentObservationClaims(documentIntelligence),
  ];
  const focalLabel = facts.find((fact) => /fell|fall|injur|contact|fire|release|damage|incident/i.test(fact)) || facts[0] || 'Incident under investigation';
  const focalId = stableId('node', `focal:${focalLabel}`);
  const nodes: CausalNode[] = [{
    id: focalId, type: 'focal-event', label: focalLabel.slice(0, 150), detail: focalLabel,
    status: 'supported', sourceIds: ['incident-description'], specialistIds: tags.map((tag) => tag.id), verified: false,
  }];
  const conditionFacts = facts.filter((fact) => /isolat|raised|removed|bled|shut|weather|scaffold|temporary|previous shift|outage/i.test(fact)).slice(0, 5);
  for (const condition of conditionFacts) {
    nodes.push({
      id: stableId('node', `condition:${condition}`), type: /previous shift|outage|removed|raised|isolat/i.test(condition) ? 'change' : 'condition',
      label: condition.slice(0, 120), detail: condition, status: 'supported', sourceIds: ['incident-description'],
      specialistIds: tags.map((tag) => tag.id), verified: false,
    });
  }
  const barrierId = stableId('node', 'barrier:prevent-event');
  nodes.push({
    id: barrierId, type: 'barrier', label: 'Required preventive or mitigating barrier is not yet established',
    detail: 'The investigation must establish what should have prevented the event or exposure and how that barrier performed.',
    status: 'unknown', sourceIds: [], specialistIds: tags.map((tag) => tag.id), verified: false,
  });
  const edges = conditionFacts.map((condition) => ({
    id: stableId('edge', `${condition}:${focalId}`), from: stableId('node', `condition:${condition}`), to: focalId,
    type: 'preceded' as const, rationale: 'The condition is chronologically relevant but its causal role is not yet verified.',
    status: 'proposed' as const, sourceIds: ['incident-description'], claimIds: [],
    counterfactual: 'Not evaluated by the deterministic preview.',
    competingExplanation: 'Not evaluated by the deterministic preview.',
    evidenceGap: 'Model causal analysis is required.', verified: false,
  }));
  const unknowns = [...new Set([...baseline.filter((question) => question.status !== 'answered').map((question) => question.text), ...questions.filter((question) => question.status !== 'answered').map((question) => question.text)])];
  const traceEntries: TraceEntry[] = [
    trace('incident-understanding', 'Established an initial situational model and opened material terminology, normal-state, and chronology gaps.', facts.slice(0, 3), baseline.filter((q) => q.status !== 'answered').map((q) => q.text)),
    trace('incident-structuring', 'Separated the incident account into facts, conditions, a focal event, and explicit unknowns.', facts, unknowns.slice(0, 4)),
    trace('tagging', 'Applied the fixed taxonomy as specialist entry points, not causal conclusions.', tags.flatMap((tag) => tag.evidence), []),
    trace('question-broker', 'Kept distinct evidence needs and preserved overlap records.', brokered.skipped.map((item) => item.intent), []),
    trace('causal-analysis', 'Created an initial investigation map; chronological conditions remain candidate causal inputs until tested.', ['incident-description'], ['Preventive barrier performance', 'Parallel causes']),
    trace('causal-verification', 'Withheld verification because the initial map still contains unsupported causal relationships.', [], ['Evidence supporting causal links'], 0.92),
  ];
  if (answers.length || documents.length) traceEntries.push(trace('revision', 'Reprocessed only this model track after new evidence was added.', [...answers.map((answer) => answer.questionId), ...documents.map((document) => document.id)], []));

  return {
    status: 'awaiting-evidence',
    structuredIncident: {
      summary: facts.slice(0, 3).join(' '), focalEvent: focalLabel,
      actualImpact: /no (?:team members|employees|one)|no injur/i.test(incident) ? 'No injury was reported in the initial account.' : 'Actual impact requires confirmation.',
      potentialImpact: 'Potential consequence requires investigation based on the exposure path.',
      normalState: 'Normal system and work configuration is not yet fully established.',
      eventState: conditionFacts.join(' ') || 'Event-time state requires additional evidence.',
      entities: [],
      timeline: facts.map((fact, index) => ({ id: stableId('event', `${index}:${fact}`), timeLabel: index === 0 ? 'Reported event' : 'Sequence not verified', sequence: index, description: fact, kind: 'event', status: 'supported', sourceIds: ['incident-description'] })),
      conditions: conditionFacts, unknowns,
    },
    facts, unknowns, baselineQuestions: baseline, tags, specialistKnowledgeBases,
    questions, skippedQuestions: brokered.skipped, answers, documentIntelligence,
    sourceAssessments: [], adjudicationConflicts: [], evidenceClaims, conflicts: [],
    answerFetches: questions.filter((question) => question.status !== 'answered').map((question) => ({
      id: stableId('fetch', question.id), questionId: question.id, status: 'not-found', answer: '', sourceIds: [], claimIds: [],
      userRequest: `Please provide what is known about: ${question.text}`,
      searched: ['reference documents', 'incident documents', 'track answers', 'specialist knowledge bases'],
    })),
    causalBoard: { maturity: 'initial', focalNodeId: focalId, nodes, edges, verificationFindings: [{
      id: stableId('verify', 'initial-evidence-gap'), targetId: focalId, severity: 'blocking',
      issue: 'The event is established, but the causal mechanism and parallel conditions are not yet verified.',
      evidenceNeeded: 'Technical system description, event sequence, barrier state, and discriminating physical or documentary evidence.',
      question: 'What evidence establishes the physical sequence and the barriers that should have prevented it?',
    }] },
    correctiveActions: [], humanDecisions: previous?.humanDecisions || [], trace: traceEntries, stageErrors: [],
    revision: previous ? { added: ['New evidence incorporated'], changed: ['Questions and investigation map re-evaluated'], resolved: [], reopened: [] } : { added: ['Initial investigation created'], changed: [], resolved: [], reopened: [] },
    documentIds: documents.map((document) => document.id),
  };
}
