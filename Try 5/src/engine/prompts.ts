import shared from '../../prompts/engine/shared.md?raw';
import read from '../../prompts/evidence-reading/task.md?raw';
import understand from '../../prompts/incident-understanding/task.md?raw';
import tag from '../../prompts/tagging/task.md?raw';
import specialist from '../../prompts/specialists/task.md?raw';
import broker from '../../prompts/question-broker/task.md?raw';
import answer from '../../prompts/answer-fetching/task.md?raw';
import review from '../../prompts/claim-review/literal.md?raw';
import interpret from '../../prompts/claim-interpretation/task.md?raw';
import causal from '../../prompts/causal-analysis/task.md?raw';
import inquiry from '../../prompts/causal-analysis/inquiry.md?raw';
import verify from '../../prompts/causal-verification/task.md?raw';
import verifyNode from '../../prompts/causal-verification/node.md?raw';
import actions from '../../prompts/corrective-actions/task.md?raw';
import { specialistPrompts } from '@/src/prompts/manifest';
import type { TagId } from '@/src/domain/types';
import type { TaskKind } from './types';
export function taskPrompt(kind: TaskKind, owner: string, verificationTarget?:'node'|'relationship') {
  if(kind==='interpret') return interpret;
  const role = kind==='verify'&&verificationTarget==='node'?verifyNode:{ read, understand, tag, specialist, broker, answer, review, causal, inquiry, verify, actions }[kind];
  // Preserve the agreed kickoff exemplars without importing old execution/schema instructions.
  const old = specialistPrompts[owner as TagId] || '';
  const mission=old.match(/## Mission\s+([\s\S]*?)(?=\n## |$)/)?.[1]?.trim()||'';
  const kickoff = old.split('\n').filter(line=>line.trimStart().startsWith('|')).join('\n');
  return `${shared}\n\n${role}${kind === 'specialist' ? `\n\nDomain mission:\n${mission}\n\nDomain kickoff examples (not a checklist to exhaust):\n${kickoff}` : ''}`;
}
