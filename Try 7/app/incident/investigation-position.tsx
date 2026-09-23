import type { AnalysisSnapshot } from '@/src/domain/types';
import { TAG_LABELS } from '@/src/domain/tag-catalog';
import type { TagId } from '@/src/domain/types';

export function InvestigationPosition({ position }: { position: NonNullable<AnalysisSnapshot['investigationPosition']> }) {
  return <section className="result-section">
    <div className="result-heading"><div><p className="eyebrow">Investigation position</p>
      <h2>{position.ready ? 'A working position — not a completed RCA' : position.stage}</h2></div></div>
    <p><strong>Provisional narrative — not a receipt of accepted changes.</strong> Claims that a revision succeeded must be checked against the board and change records.</p>
    <p>{position.summary || 'Reading the supplied sources before selecting explanations and evidence directions.'}</p>
    <p>{position.notebookCount} source observations preserved · {position.selectedCount} selected map premises · {position.reusedSourceSpans} unchanged source passages reused.</p>
    {!!position.revisionReason && <p>Proposed rationale / revision admission note: {position.revisionReason}</p>}
    {position.proposedNarrative&&<details><summary>Unreconciled model narrative — some proposed changes were rejected</summary><p>{position.proposedNarrative.summary}</p><p>{position.proposedNarrative.reason}</p></details>}
    <div className="foundation-grid">{position.branches.map(b => <article key={b.id}>
      <span>Possible explanation · {b.status}</span><h3>{b.title}</h3><p>{b.mechanism}</p>
      <p><strong>What remains uncertain:</strong> {b.gap}</p>
      {!!b.applicability && <p><strong>Applies when:</strong> {b.applicability}</p>}
      {!!b.assumptions?.length && <p><strong>Assumptions, not facts:</strong> {b.assumptions.join(' · ')}</p>}
      {!!b.conditions?.length && <details><summary>Required conditions</summary>{b.conditions.map(c=><p key={c.id}><strong>{c.status}:</strong> {c.statement}<br />{c.scope}<br />Expected evidence: {c.expectedObservation}</p>)}</details>}
      {!!b.distinguishes?.length && <details><summary>Distinguishing observations</summary>{b.distinguishes.map((d,i)=><p key={i}>{d.observation}<br />If established: {d.ifEstablished}<br />If reliably ruled out: {d.ifRuledOut}</p>)}</details>}
      <details><summary>Supporting and opposing observations</summary>
        <p>These are source observations, not proof that this explanation is true.</p>
        <ul>{b.supporting.map((s, i) => <li key={'s'+i}>Consistent with: {s}</li>)}{b.opposing.map((s, i) => <li key={'o'+i}>Against: {s}</li>)}</ul>
        <p>{b.changeReason}</p></details>
    </article>)}</div>
    {!!position.pendingImpacts?.length && <p role="status">Unresolved evidence impacts: {position.pendingImpacts.join(', ')}. No completed impact assessment is implied.</p>}
    {!!position.impacts?.length && <details><summary>Evidence impact decisions</summary>{position.impacts.map((impact,i)=><p key={i}>V{impact.version} · {impact.action} · {impact.targetId}<br />{impact.reason}</p>)}</details>}
    {!!position.directions.length && <details open><summary>Evidence that would change the next version</summary>
      {position.directions.map(d => <article className="question-card" key={d.questionId}>
        <span>{d.priority} · {d.status.replaceAll('-', ' ')}</span><h3>{d.question}</h3><p>{d.evidenceNeeded}</p>
        <p><strong>If established:</strong> {d.ifPresent}</p><p><strong>If reliably ruled out:</strong> {d.ifAbsent}</p>
        <a href={`#question-${d.questionId}`}>Answer or attach the requested record</a>
        <p><small>A missing document does not establish a negative result.</small></p>
      </article>)}
    </details>}
    {!!position.consultations.length && <details><summary>Why specialists were consulted</summary>
      {position.consultations.map(c => <article className="question-card" key={c.id}><strong>{TAG_LABELS[c.domain as TagId] || c.domain}</strong>
        <p>{c.purpose}</p><p>{c.summary || 'Consultation pending or incomplete.'}</p><small>{c.limitations}</small>
        {c.completedVersion && <p>Completed in V{c.completedVersion}; retained unless new evidence changes its premises.</p>}</article>)}
    </details>}
  </section>;
}
