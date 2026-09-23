'use client';
import type { AnalysisSnapshot } from '@/src/domain/types';
export function EngineProgress({ progress, onRetry, onRefresh, onPause }: {
  progress: NonNullable<AnalysisSnapshot['engineProgress']>; onRetry: () => void; onRefresh: () => void; onPause?:()=>void;
}) {
  const done = progress.tasks.filter(t => t.status === 'completed');
  const failures = progress.tasks.filter(t => t.status === 'failed' || t.status === 'blocked');
  const superseded = progress.tasks.filter(t => t.status === 'superseded');
  return <section className="result-section" aria-live="polite">
    <div className="section-heading"><div><p className="eyebrow">Try 6 investigation-led engine</p><h2>Execution: {progress.status}</h2></div></div>
    <p>{done.length} / {progress.tasks.length} scheduled tasks completed · {done.filter(t => t.reused).length} reused · {failures.length} failed/blocked · {superseded.length} superseded (not executed) · {progress.quarantineCount} quarantined items.</p>
    <p>Execution completion is not a verified RCA. Evidence support and human approval are separate.</p>
    {progress.model&&<p>Model: {progress.model.id} · context {progress.model.contextWindow?.toLocaleString()||'provider default'} · engine {progress.model.engineVersion}<br/><small>Digest: {progress.model.digest||'Not supplied by this provider'}</small></p>}
    <p>{progress.tasks.reduce((n,t) => n+t.inputTokens,0).toLocaleString()} reported input tokens · {progress.tasks.reduce((n,t) => n+t.outputTokens,0).toLocaleString()} output tokens.</p>
    <button className="button ghost-button" type="button" onClick={onRefresh}>Refresh progress</button>
    {['queued','running'].includes(progress.status)&&onPause&&<button className="button" type="button" onClick={onPause}>Pause investigation</button>}
    {progress.status === 'partial' && <button className="button" type="button" onClick={onRetry}>Retry failed work in a new revision</button>}
    {progress.pauseReason&&<p role="status">{progress.pauseReason}</p>}
    {progress.status === 'paused' && <button className="button" type="button" onClick={onRetry}>{progress.pauseReason?.startsWith('Evidence-reading checkpoint:')?'Approve evidence checkpoint and continue':'Resume after reviewing the stop reason'}</button>}
    <details><summary>Tasks, evidence coverage, and failures</summary>
      {progress.tasks.map(t => <article className="question-card" key={t.id}>
        <strong>{t.kind} · {t.owner} · {t.status}{t.reused ? ' · reused' : ''}</strong>
        {t.target&&<p>{t.target}</p>}
        {t.decision&&<p>Decision summary: {t.decision}</p>}
        <p>Attempt {t.attempts}; {t.evidenceCount} selected source spans; {t.omittedEvidenceCount} matching spans outside this working set; {t.contextBytes.toLocaleString()} request bytes.</p>
        {t.error && <p className={t.status === 'superseded' ? undefined : 'form-error'}>{t.error}</p>}
        {t.traceId&&<p><a href={`/api/engine/calls/${t.traceId}`} target="_blank" rel="noreferrer">Inspect exact request and preserved raw response</a></p>}
      </article>)}
    </details>
    {!!progress.quarantine?.length&&<details><summary>Quarantined output items</summary>{progress.quarantine.map((q,i)=><p key={i}>{q.reason} <small>Task {q.taskId}</small></p>)}</details>}
    <details><summary>What changed and why</summary>{progress.changes.map((c,i) => <p key={i}><strong>{c.kind}</strong> · {c.reason} <small>{c.targetId}</small></p>)}</details>
    <details><summary>Original-source coverage</summary>{progress.sourceCoverage.map(s => <p key={s.id}>{s.label}: {s.readSpans??0} / {s.spans} preserved spans read successfully. {s.limitations.join(' ')}</p>)}</details>
  </section>;
}
