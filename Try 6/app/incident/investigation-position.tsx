import type { AnalysisSnapshot } from '@/src/domain/types';
import { TAG_LABELS } from '@/src/domain/tag-catalog';
import type { TagId } from '@/src/domain/types';

export function InvestigationPosition({ position }: { position: NonNullable<AnalysisSnapshot['investigationPosition']> }) {
  return <section className="result-section">
    <div className="result-heading"><div><p className="eyebrow">Investigation position</p>
      <h2>{position.ready ? 'A working position — not a completed RCA' : position.stage}</h2></div></div>
    <p>{position.summary || 'Reading the supplied sources before selecting explanations and evidence directions.'}</p>
    <p>{position.notebookCount} source observations preserved · {position.selectedCount} selected map premises · {position.reusedSourceSpans} unchanged source passages reused.</p>
    {!!position.revisionReason && <p>Why this position: {position.revisionReason}</p>}
    <div className="foundation-grid">{position.branches.map(b => <article key={b.id}>
      <span>Possible explanation · {b.status}</span><h3>{b.title}</h3><p>{b.mechanism}</p>
      <p><strong>What remains uncertain:</strong> {b.gap}</p>
      <details><summary>Supporting and opposing observations</summary>
        <p>These are source observations, not proof that this explanation is true.</p>
        <ul>{b.supporting.map((s, i) => <li key={'s'+i}>Consistent with: {s}</li>)}{b.opposing.map((s, i) => <li key={'o'+i}>Against: {s}</li>)}</ul>
        <p>{b.changeReason}</p></details>
    </article>)}</div>
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
