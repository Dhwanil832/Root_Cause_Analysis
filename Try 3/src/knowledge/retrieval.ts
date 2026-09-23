import type { DocumentRecord, InvestigationAnswer, InvestigationQuestion, SpecialistKnowledgeBase } from '@/src/domain/types';

const STOP = new Set(['what', 'when', 'where', 'which', 'with', 'were', 'was', 'that', 'this', 'from', 'have', 'been', 'could', 'would', 'should', 'there', 'their', 'about', 'into', 'during', 'before', 'after']);

function terms(value: string) {
  return [...new Set(value.toLowerCase().match(/[a-z0-9][a-z0-9-]{2,}/g) || [])]
    .filter((term) => !STOP.has(term));
}

function excerpt(text: string, needles: string[]) {
  const lowered = text.toLowerCase();
  const index = needles.map((term) => lowered.indexOf(term)).filter((value) => value >= 0).sort((a, b) => a - b)[0] || 0;
  const start = Math.max(0, index - 420);
  return text.slice(start, start + 2_400);
}

export function retrieveForQuestion(
  question: InvestigationQuestion,
  documents: DocumentRecord[],
  answers: InvestigationAnswer[],
  knowledgeBases: SpecialistKnowledgeBase[],
) {
  const needles = terms(`${question.text} ${question.intent} ${question.evidenceNeeded.join(' ')}`);
  const sources: Array<{ sourceId: string; label: string; scope: string; excerpt: string; score: number }> = [];
  for (const document of documents) {
    if (!document.extractedText) continue;
    const lowered = document.extractedText.toLowerCase();
    const score = needles.reduce((total, term) => total + (lowered.includes(term) ? 1 : 0), 0);
    if (score > 0) sources.push({ sourceId: document.id, label: document.title, scope: document.scope, excerpt: excerpt(document.extractedText, needles), score });
  }
  for (const answer of answers) {
    const lowered = answer.text.toLowerCase();
    const score = needles.reduce((total, term) => total + (lowered.includes(term) ? 1 : 0), 0);
    if (score > 0) sources.push({ sourceId: answer.sourceId || `answer:${answer.questionId}`, label: `Answer to ${answer.questionId}`, scope: 'answer', excerpt: answer.text.slice(0, 2_400), score });
  }
  for (const kb of knowledgeBases) {
    const body = [kb.summary, ...kb.findings.map((finding) => finding.statement)].join('\n');
    const lowered = body.toLowerCase();
    const score = needles.reduce((total, term) => total + (lowered.includes(term) ? 1 : 0), 0);
    if (score > 1) sources.push({ sourceId: `kb:${kb.tagId}`, label: `${kb.label} knowledge base`, scope: 'specialist-kb', excerpt: excerpt(body, needles), score });
  }
  return sources.sort((a, b) => b.score - a.score).slice(0, 8);
}
