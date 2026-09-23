import { QUESTION_CATALOG, TAG_KEYWORDS, TAG_LABELS } from '@/src/domain/tag-catalog';
import type {
  AnalysisSnapshot,
  InvestigationAnswer,
  InvestigationQuestion,
  SkippedQuestion,
  TagId,
  TagResult,
  TraceEntry,
} from '@/src/domain/types';

const PROMPT_VERSION = 'try2.1.0';

function stableId(prefix: string, value: string) {
  let hash = 2166136261;
  for (const char of value) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return prefix + '-' + (hash >>> 0).toString(36);
}

function sentences(text: string) {
  return text
    .split(/(?<=[.!?])\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function containsKeyword(text: string, keyword: string) {
  const escaped = keyword.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&');
  return new RegExp('(^|[^a-z0-9])' + escaped + '([^a-z0-9]|$)', 'i').test(text);
}

function excerpts(text: string, keywords: string[]) {
  const lowered = text.toLowerCase();
  return sentences(text)
    .filter((sentence) => keywords.some((word) => containsKeyword(sentence, word)))
    .slice(0, 3)
    .map((sentence) => {
      const index = lowered.indexOf(sentence.toLowerCase());
      return index >= 0 ? 'Incident text: “' + sentence.slice(0, 180) + '”' : sentence;
    });
}

function extractTerms(text: string) {
  const quoted = [...text.matchAll(/(?:\b[A-Z][A-Za-z0-9-]*\s+){0,4}\b(?:Beam|Yoke|Pit|Mill|System|Stand|Balance|Carrier)\b/g)]
    .map((match) => match[0].trim());
  const identifiers = [...text.matchAll(/\b[A-Z]\d{1,3}\b/g)].map((match) => match[0]);
  return [...new Set([...quoted, ...identifiers])].slice(0, 5);
}

function makeBaselineQuestions(text: string, answers: InvestigationAnswer[]) {
  const terms = extractTerms(text);
  const questions: InvestigationQuestion[] = [];
  if (terms.length) {
    const named = terms.join(', ');
    questions.push({
      id: stableId('bq', 'terms-' + named),
      tagId: 'baseline',
      text: 'In this site and process, what are ' + named + ', and how do they normally relate to one another?',
      intent: 'site-vocabulary',
      rationale: 'The report uses site-specific names whose function and relationship cannot safely be assumed.',
      evidenceNeeded: ['annotated equipment diagram', 'plain-language explanation', 'asset hierarchy'],
      priority: 'high',
      status: 'open',
    });
  }
  questions.push({
    id: stableId('bq', 'normal-vs-event'),
    tagId: 'baseline',
    text: 'What was the normal operating configuration, and exactly what was different at the time of the incident?',
    intent: 'normal-vs-event',
    rationale: 'A causal investigation needs a reliable baseline before interpreting abnormal conditions.',
    evidenceNeeded: ['normal arrangement drawing', 'pre-event configuration record'],
    priority: 'high',
    status: 'open',
  });
  if (/\b(previous shift|morning|prior|throughout|at approximately|outage)\b/i.test(text)) {
    questions.push({
      id: stableId('bq', 'timeline'),
      tagId: 'baseline',
      text: 'What is the verified timeline from the last known normal condition through the event, including work by earlier shifts and contractors?',
      intent: 'event-timeline',
      rationale: 'The description spans multiple times or work groups and may omit important state changes.',
      evidenceNeeded: ['shift logs', 'work orders', 'access records', 'witness chronology'],
      priority: 'high',
      status: 'open',
    });
  }
  return questions.map((question) => ({
    ...question,
    status: answers.some((answer) => answer.questionId === question.id && answer.text.trim())
      ? 'answered' as const
      : question.status,
  }));
}

function selectTags(text: string): TagResult[] {
  const lowered = text.toLowerCase();
  const selected: TagResult[] = [];
  for (const [id, keywords] of Object.entries(TAG_KEYWORDS) as Array<[TagId, string[]]>) {
    if (id === 'other-novel') continue;
    const hits = keywords.filter((keyword) => containsKeyword(lowered, keyword));
    if (!hits.length) continue;
    selected.push({
      id,
      label: TAG_LABELS[id],
      rationale: 'The account directly references ' + hits.slice(0, 3).join(', ') + ', making this a material direction to screen.',
      evidence: excerpts(text, hits),
      confidence: Math.min(0.96, 0.61 + hits.length * 0.07),
    });
  }
  return selected;
}

function buildSpecialistQuestions(tags: TagResult[], answers: InvestigationAnswer[]) {
  const proposed: InvestigationQuestion[] = [];
  for (const tag of tags) {
    for (const candidate of QUESTION_CATALOG[tag.id]) {
      const id = stableId('q', tag.id + '-' + candidate.intent);
      proposed.push({
        id,
        tagId: tag.id,
        text: candidate.text,
        intent: candidate.intent,
        rationale: candidate.rationale,
        evidenceNeeded: candidate.evidence,
        priority: ['energy-state', 'release-sequence', 'physical-condition', 'work-scope'].includes(candidate.intent)
          ? 'high'
          : 'medium',
        status: answers.some((answer) => answer.questionId === id && answer.text.trim())
          ? 'answered'
          : 'open',
      });
    }
  }
  return proposed;
}

function brokerQuestions(
  baseline: InvestigationQuestion[],
  proposed: InvestigationQuestion[],
): { questions: InvestigationQuestion[]; skipped: SkippedQuestion[] } {
  const kept: InvestigationQuestion[] = [];
  const skipped: SkippedQuestion[] = [];
  const intentOwners = new Map<string, InvestigationQuestion>();
  for (const question of [...baseline, ...proposed]) {
    const owner = intentOwners.get(question.intent);
    if (!owner) {
      intentOwners.set(question.intent, question);
      if (question.tagId !== 'baseline') kept.push(question);
      continue;
    }
    if (question.tagId === 'baseline') continue;
    skipped.push({
      id: stableId('sq', question.id + '-' + owner.id),
      proposedBy: question.tagId,
      text: question.text,
      intent: question.intent,
      coveredByQuestionId: owner.id,
      coveredByTagId: owner.tagId,
      reason: 'Skipped because the existing question covers the same investigation intent and evidence boundary.',
    });
  }
  return { questions: kept, skipped };
}

function trace(stage: TraceEntry['stage'], summary: string, evidence: string[], unknowns: string[], confidence: number, start: number): TraceEntry {
  return {
    id: stableId('trace', stage + '-' + summary),
    stage,
    summary,
    evidence,
    unknowns,
    confidence,
    promptVersion: PROMPT_VERSION,
    engine: 'deterministic-preview',
    durationMs: Math.max(1, Date.now() - start),
  };
}

export function runDeterministicAnalysis(
  incident: string,
  answers: InvestigationAnswer[] = [],
): AnalysisSnapshot {
  const started = Date.now();
  const trackEvidence = [
    incident,
    ...answers.map((answer) => 'Investigator answer: ' + answer.text),
  ].join('\n');
  const baselineQuestions = makeBaselineQuestions(incident, answers);
  const tags = selectTags(trackEvidence);
  const proposed = buildSpecialistQuestions(tags, answers);
  const brokered = brokerQuestions(baselineQuestions, proposed);
  const facts = sentences(incident).slice(0, 8);
  const unansweredBaseline = baselineQuestions.filter((q) => q.status === 'open');
  const traceEntries: TraceEntry[] = [
    trace('baseline', 'Separated the initial account into stated facts and context gaps; generated only material baseline clarifications.', facts.slice(0, 3), unansweredBaseline.map((q) => q.text), 0.78, started),
    trace('tagging', 'Applied the fixed tag taxonomy as investigation entry points, not causal conclusions.', tags.flatMap((tag) => tag.evidence).slice(0, 5), [], tags.length ? 0.84 : 0.42, started),
    trace('specialists', 'Each selected tag proposed questions within its own subject boundary.', tags.map((tag) => tag.label), [], 0.8, started),
    trace('broker', 'Merged questions with the same stable intent while preserving who proposed and who covered each skipped question.', brokered.skipped.map((item) => item.intent), [], 0.91, started),
  ];
  if (answers.length) {
    traceEntries.push(trace('revision', 'Re-ran this model track using its own prior answers; no evidence was shared with another model.', answers.map((answer) => answer.questionId), [], 0.87, started));
  }
  return {
    facts,
    unknowns: unansweredBaseline.map((question) => question.text),
    baselineQuestions,
    tags,
    questions: brokered.questions,
    skippedQuestions: brokered.skipped,
    trace: traceEntries,
    answers,
  };
}
