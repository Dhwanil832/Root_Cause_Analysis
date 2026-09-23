'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { IncidentRecord, InvestigationQuestion, TagId, TrackRecord, VersionRecord } from '@/src/domain/types';
import { TAG_LABELS } from '@/src/domain/tag-catalog';
import { CausalCanvas } from './causal-canvas';

function formatTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  }).format(new Date(value));
}

function tagLabel(value: string) {
  if (value === 'baseline') return 'Step 0';
  if (value === 'causal-analysis') return 'Causal analysis';
  if (value === 'causal-verification') return 'Causal verification';
  return TAG_LABELS[value as TagId] || value.replaceAll('-', ' ');
}

function QuestionCard({
  question,
  trackId,
  existingAnswer,
  onSaved,
}: {
  question: InvestigationQuestion;
  trackId: string;
  existingAnswer?: string;
  onSaved: () => Promise<void>;
}) {
  const [answer, setAnswer] = useState(existingAnswer || '');
  const [file, setFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function save() {
    if (!answer.trim() && !file) return;
    setSaving(true);
    setError('');
    try {
      let fileData: { fileKey?: string; fileName?: string; excerpt?: string } = {};
      if (file) {
        const form = new FormData();
        form.append('file', file);
        form.append('trackId', trackId);
        form.append('questionId', question.id);
        const upload = await fetch('/api/uploads', { method: 'POST', body: form });
        fileData = await upload.json() as typeof fileData & { error?: string };
        if (!upload.ok) throw new Error((fileData as { error?: string }).error || 'Upload failed.');
      }
      const combinedAnswer = [answer.trim(), fileData.excerpt
        ? 'Document excerpt:\n' + fileData.excerpt
        : ''].filter(Boolean).join('\n\n');
      const response = await fetch('/api/tracks/' + trackId + '/versions', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          questionId: question.id,
          answer: combinedAnswer || 'Evidence document attached.',
          fileKey: fileData.fileKey,
          fileName: fileData.fileName,
        }),
      });
      const result = await response.json() as { error?: string };
      if (!response.ok) throw new Error(result.error || 'Could not create a new version.');
      await onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not save the answer.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className={'question-card' + (question.status === 'answered' ? ' answered' : '')}>
      <div className="question-topline">
        <span>{question.priority} priority</span>
        <span>{question.intent.replaceAll('-', ' ')}</span>
      </div>
      <h3>{question.text}</h3>
      <details className="question-context">
        <summary>Why this is being asked</summary>
        <p>{question.rationale}</p>
        <p><strong>Useful evidence:</strong> {question.evidenceNeeded.join(', ')}</p>
      </details>
      <textarea
        rows={3}
        value={answer}
        onChange={(event) => setAnswer(event.target.value)}
        placeholder="Answer with what is known. It is valid to state that the fact is currently unknown."
      />
      <div className="answer-actions">
        <label className="file-button">
          <input type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} />
          {file ? file.name : 'Attach evidence'}
        </label>
        <button className="button save-button" type="button" onClick={save}
          disabled={saving || (!answer.trim() && !file)}>
          {saving ? 'Creating version…' : existingAnswer ? 'Create revised version' : 'Answer & create version'}
        </button>
      </div>
      {error && <p className="form-error">{error}</p>}
    </article>
  );
}

export function InvestigationDashboard({ incidentId }: { incidentId: string }) {
  const [incident, setIncident] = useState<IncidentRecord | null>(null);
  const [trackId, setTrackId] = useState('');
  const [versionId, setVersionId] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async (selectLatest = false) => {
    const response = await fetch('/api/incidents/' + incidentId, { cache: 'no-store' });
    const payload = await response.json() as { incident?: IncidentRecord; error?: string };
    if (!response.ok || !payload.incident) {
      setError(payload.error || 'Unable to load the incident.');
      return;
    }
    setIncident(payload.incident);
    const nextTrack = payload.incident.tracks.find((track) => track.id === trackId)
      || payload.incident.tracks[0];
    if (nextTrack) {
      setTrackId(nextTrack.id);
      const latest = nextTrack.versions.at(-1);
      if (selectLatest && latest) setVersionId(latest.id);
      else if (!nextTrack.versions.some((version) => version.id === versionId) && latest) {
        setVersionId(latest.id);
      }
    }
  }, [incidentId, trackId, versionId]);

  const [resuming, setResuming] = useState(false);
  const [resumeError, setResumeError] = useState('');
  const autoStarted = useRef(false);
  useEffect(() => {
    if (!incident || autoStarted.current || new URLSearchParams(window.location.search).get('start') !== '1') return;
    autoStarted.current = true;
    window.history.replaceState(null, '', window.location.pathname);
    void (async () => {
      setResuming(true);
      try {
        // The initial click authorizes this pass; refreshes never auto-retry it.
        for (const selected of incident.tracks.filter(t => !t.versions.length)) {
          const response = await fetch(`/api/tracks/${selected.id}/initialize`, { method: 'POST' });
          const result = await response.json() as { error?: string };
          if (!response.ok) throw new Error(result.error || 'Initialization stopped; completed calls are preserved.');
          await load(true);
        }
      } catch (error) { setResumeError(error instanceof Error ? error.message : 'Investigation stopped.'); }
      finally { setResuming(false); await load(); }
    })();
  }, [incident, load]);
  async function resume() {
    if (!trackId) return;
    setResuming(true); setResumeError('');
    try {
      const response = await fetch(`/api/tracks/${trackId}/resume`, { method: 'POST' });
      const result = await response.json() as { error?: string };
      if (!response.ok) throw new Error(result.error || 'Resume failed.');
      await load(true);
    } catch (error) { setResumeError(error instanceof Error ? error.message : 'Resume failed.'); }
    finally { setResuming(false); await load(); }
  }

  useEffect(() => {
    if (!incident || (!resuming && incident.tracks.every(t => t.versions.length))) return;
    const timer = window.setInterval(() => { void load(); }, 10_000);
    return () => window.clearInterval(timer);
  }, [incident, resuming, load]);

  useEffect(() => {
    let cancelled = false;
    fetch('/api/incidents/' + incidentId, { cache: 'no-store' })
      .then(async (response) => {
        const payload = await response.json() as { incident?: IncidentRecord; error?: string };
        if (!response.ok || !payload.incident) {
          throw new Error(payload.error || 'Unable to load the incident.');
        }
        return payload.incident;
      })
      .then((loaded) => {
        if (cancelled) return;
        setIncident(loaded);
        const firstTrack = loaded.tracks[0];
        if (firstTrack) {
          setTrackId(firstTrack.id);
          setVersionId(firstTrack.versions.at(-1)?.id || '');
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : 'Unable to load the incident.');
        }
      });
    return () => { cancelled = true; };
  }, [incidentId]);

  const track = useMemo<TrackRecord | undefined>(
    () => incident?.tracks.find((item) => item.id === trackId) || incident?.tracks[0],
    [incident, trackId],
  );
  const version = useMemo<VersionRecord | undefined>(
    () => track?.versions.find((item) => item.id === versionId) || track?.versions.at(-1),
    [track, versionId],
  );

  function chooseTrack(nextTrack: TrackRecord) {
    setTrackId(nextTrack.id);
    setVersionId(nextTrack.versions.at(-1)?.id || '');
  }

  async function reviewCorrectiveAction(actionId: string) {
    if (!track) return;
    const response = await fetch(`/api/tracks/${track.id}/review`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ targetType: 'corrective-action', targetId: actionId, action: 'approve' }),
    });
    const payload = await response.json() as { error?: string };
    if (!response.ok) { setError(payload.error || 'Unable to approve the corrective action.'); return; }
    await load(true);
  }

  async function reviewDocumentObservation(observationId: string, action: 'accept' | 'reject') {
    if (!track) return;
    const response = await fetch(`/api/tracks/${track.id}/review`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        targetType: 'document-observation',
        targetId: observationId,
        action,
        notes: action === 'accept'
          ? 'Confirmed against the preserved source.'
          : 'Rejected after reviewing the preserved source.',
      }),
    });
    const payload = await response.json() as { error?: string };
    if (!response.ok) {
      setError(payload.error || 'Unable to review the document observation.');
      return;
    }
    await load(true);
  }

  if (error) {
    return <main className="center-page"><div className="processing-card"><h1>{error}</h1><Link href="/history">Return to history</Link></div></main>;
  }
  if (!incident || !track) {
    return <main className="center-page"><div className="processing-card"><p>Loading investigation…</p></div></main>;
  }
  const pending = track.checkpoints?.filter(c => c.targetVersion > (track.versions.at(-1)?.number || 0)) || [];
  const completedCalls = pending.filter(c => (c.payload as { kind?: string })?.kind === 'model-call').length;
  const progress = <section className="result-section">
    <h3>{version ? 'Uncommitted investigation work' : 'No causal version committed yet'}</h3>
    <p>{completedCalls} completed model calls preserved. Resume reuses matching inputs, prompts and model configuration; changed inputs are recalculated.</p>
    {pending.at(-1) && <p>Latest checkpoint: {tagLabel(pending.at(-1)!.stage)} · {pending.at(-1)!.status}</p>}
    <button type="button" className="button" onClick={resume} disabled={resuming}>{resuming ? 'Resuming saved work…' : 'Resume investigation'}</button>
    <button type="button" className="button ghost-button" onClick={() => load()}>Refresh progress</button>
    {resumeError && <p className="form-error">{resumeError}</p>}
  </section>;
  if (!version) return <main className="center-page"><div className="processing-card">
    <h1>{incident.title}</h1><p>{incident.description}</p>
    <label>Model <select value={trackId} onChange={e => setTrackId(e.target.value)}>{incident.tracks.map(t => <option key={t.id} value={t.id}>{t.modelName}</option>)}</select></label>
    {progress}<Link href="/history">Return to history</Link>
  </div></main>;

  const analysis = version.analysis;
  const answerMap = new Map(analysis.answers.map((answer) => [answer.questionId, answer.text]));
  const allQuestions = [...analysis.baselineQuestions, ...analysis.questions];
  const visibleDocuments = track.documents.filter((document) =>
    !document.introducedVersion || document.introducedVersion <= version.number,
  );
  const grouped = allQuestions.reduce<Record<string, InvestigationQuestion[]>>((result, question) => {
    const key = question.tagId;
    result[key] = [...(result[key] || []), question];
    return result;
  }, {});

  return (
    <main className="dashboard-shell">
      <header className="dashboard-header">
        <Link className="brand" href="/"><span className="brand-mark">R</span><span>RCA Fieldwork</span></Link>
        <div className="breadcrumb"><Link href="/history">History</Link><span>/</span><span>{incident.title}</span></div>
        <Link className="button ghost-button" href="/">New incident</Link>
      </header>

      <div className="dashboard-grid">
        <aside className="run-sidebar">
          <p className="eyebrow">Incident</p>
          <h1>{incident.title}</h1>
          <button className="description-toggle" type="button">
            Original description · immutable
          </button>
          <p className="incident-description">{incident.description}</p>

          <div className="sidebar-section">
            <p className="eyebrow">Model tracks</p>
            {incident.tracks.map((item) => (
              <button key={item.id}
                className={'track-button' + (item.id === track.id ? ' active' : '')}
                onClick={() => chooseTrack(item)} type="button">
                <span><strong>{item.modelName}</strong><small>{item.provider}</small></span>
                <span>V{item.versions.at(-1)?.number}</span>
              </button>
            ))}
          </div>
        </aside>

        <section className="investigation-main">
          <div className="investigation-titlebar">
            <div>
              <p className="eyebrow">Independent model track</p>
              <h2>{track.modelName}</h2>
              <p>No answers or evidence from other models enter this track.</p>
            </div>
            <span className="engine-badge">{track.provider}</span>
          </div>

          <div className="version-strip" aria-label="Versions">
            {track.versions.map((item) => (
              <button type="button" key={item.id}
                className={item.id === version.id ? 'active' : ''}
                onClick={() => setVersionId(item.id)}>
                <strong>V{item.number}</strong>
                <small>{formatTime(item.createdAt)}</small>
              </button>
            ))}
          </div>

          <div className="snapshot-banner">
            <span>Viewing V{version.number}</span>
            <p>{version.trigger}</p>
            <span className={`case-status ${analysis.status}`}>{analysis.status.replaceAll('-', ' ')}</span>
          </div>
          {pending.length > 0 && progress}
          <p className="execution-state">Execution: {analysis.stageErrors.length ? 'incomplete — stage failures recorded' : 'completed'} · Evidence review: {analysis.causalBoard.verificationFindings.some(f => f.severity === 'blocking') ? 'unresolved findings remain' : 'ready for human review; not human-approved'}</p>

          <div className="report-shortcuts">
            {track.modelId.startsWith('ollama:') && <Link className="button ghost-button" href={`/story/${track.id}`}>Story simulator</Link>}
            <Link className="button ghost-button" href={`/incident/${incident.id}/report?trackId=${track.id}&versionId=${version.id}`}>Open investigation report</Link>
          </div>

          <section className="result-section case-foundation">
            <div className="result-heading">
              <div><p className="eyebrow">Case foundation</p><h2>What the investigation currently understands</h2></div>
              <span>{analysis.answers.length} preserved answers · {visibleDocuments.length} documents</span>
            </div>
            <div className="foundation-grid">
              <article className="foundation-summary"><span>Focal event</span><h3>{analysis.structuredIncident.focalEvent}</h3><p>{analysis.structuredIncident.summary}</p></article>
              <article><span>Normal state</span><p>{analysis.structuredIncident.normalState}</p></article>
              <article><span>Event state</span><p>{analysis.structuredIncident.eventState}</p></article>
              <article><span>Actual impact</span><p>{analysis.structuredIncident.actualImpact}</p></article>
              <article><span>Potential impact</span><p>{analysis.structuredIncident.potentialImpact}</p></article>
            </div>
            {(analysis.structuredIncident.entities.length > 0 || analysis.structuredIncident.timeline.length > 0) && (
              <div className="foundation-details">
                <details><summary>Entities · {analysis.structuredIncident.entities.length}</summary><ul>{analysis.structuredIncident.entities.map((entity) => <li key={entity.id}><strong>{entity.name}</strong> — {entity.description}</li>)}</ul></details>
                <details><summary>Working timeline · {analysis.structuredIncident.timeline.length}</summary><ol>{analysis.structuredIncident.timeline.map((event) => <li key={event.id}><strong>{event.timeLabel}</strong> — {event.description}</li>)}</ol></details>
              </div>
            )}
          </section>

          <section className="result-section">
            <div className="result-heading">
              <div><p className="eyebrow">Source adjudication</p><h2>{analysis.sourceAssessments.length} assessed sources · {analysis.adjudicationConflicts.length} source conflicts</h2></div>
              <span>Authority, applicability, revision status, directness, and reliability are evaluated before causal use.</span>
            </div>
            {analysis.adjudicationConflicts.length > 0 && <div className="conflict-list">{analysis.adjudicationConflicts.map((conflict) => <article key={conflict.id}><strong>{conflict.summary}</strong><p>{conflict.resolutionNeeded}</p><span>{conflict.sourceIds.join(' · ')}</span></article>)}</div>}
            <div className="claim-grid">{analysis.sourceAssessments.map((source) => <article key={source.sourceId}><div><span>{source.sourceId}</span><b className={`evidence-status ${source.reliability === 'high' ? 'verified' : source.reliability === 'low' ? 'contradicted' : 'proposed'}`}>{source.reliability} reliability</b></div><p>{source.label}</p><small>{source.authority} authority · {source.directness} · {source.applicability} · {source.revisionStatus}</small>{source.limitations.length > 0 && <p>Limits: {source.limitations.join(' · ')}</p>}</article>)}</div>
          </section>

          <section className="result-section">
            <div className="result-heading">
              <div><p className="eyebrow">Preserved evidence inputs</p><h2>Three separate document scopes</h2></div>
              <span>Each track sees only its own preserved attachments.</span>
            </div>
            <div className="document-scope-grid">
              {(['reference', 'starter', 'question'] as const).map((scope) => {
                const scoped = visibleDocuments.filter((document) => document.scope === scope);
                const heading = scope === 'reference' ? 'Default references' : scope === 'starter' ? 'Incident starter records' : 'Question-response evidence';
                return <article key={scope} className="document-scope"><div><span>{scope}</span><strong>{heading}</strong><b>{scoped.length}</b></div>{scoped.length === 0 ? <p>No documents in this scope.</p> : <ul>{scoped.map((document) => <li key={document.id}><a href={`/api/documents/${document.id}/content`} target="_blank" rel="noreferrer"><strong>{document.title}</strong></a><span>Rev {document.revision} · {document.extractionStatus}</span></li>)}</ul>}</article>;
              })}
            </div>
          </section>

          <section className="result-section">
            <div className="result-heading">
              <div><p className="eyebrow">Document &amp; image intelligence</p><h2>Model readings tied to preserved originals</h2></div>
              <span>Observations remain proposed until an investigator confirms them.</span>
            </div>
            {(analysis.documentIntelligence || []).length === 0 && (
              <div className="empty-panel"><h3>No document interpretations in this version</h3><p>Attach an image or document to let this model track examine it.</p></div>
            )}
            <div className="document-intelligence-grid">
              {(analysis.documentIntelligence || []).map((record) => (
                <article className="document-intelligence-card" key={record.documentId}>
                  {record.contentType.startsWith('image/') && (
                    <a className="evidence-preview" href={`/api/documents/${record.documentId}/content`} target="_blank" rel="noreferrer">
                      <Image src={`/api/documents/${record.documentId}/content`} alt={`Preserved evidence: ${record.title}`} width={900} height={540} unoptimized />
                    </a>
                  )}
                  <div className="document-intelligence-heading">
                    <div><span>{record.mode.replaceAll('-', ' ')}</span><h3>{record.title}</h3></div>
                    <a href={`/api/documents/${record.documentId}/content`} target="_blank" rel="noreferrer">Open original</a>
                  </div>
                  <p>{record.summary}</p>
                  <small>{record.documentType} · {record.engine}</small>
                  {record.limitations.length > 0 && <div className="evidence-limitations"><strong>Limitations</strong><ul>{record.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul></div>}
                  {record.observations.length > 0 && <div className="observation-list">{record.observations.map((observation) => (
                    <article key={observation.id}>
                      <div><span>{observation.kind.replaceAll('-', ' ')}</span><b className={`evidence-status ${observation.status}`}>{observation.status}</b></div>
                      <p>{observation.text}</p>
                      <small>{observation.location || 'Location not isolated'} · {Math.round(observation.confidence * 100)}% model confidence{observation.requiresVerification ? ' · verification requested' : ''}</small>
                      {observation.status !== 'verified' && observation.status !== 'rejected' && <div className="observation-actions"><button type="button" onClick={() => reviewDocumentObservation(observation.id, 'accept')}>Confirm observation</button><button type="button" onClick={() => reviewDocumentObservation(observation.id, 'reject')}>Reject</button></div>}
                    </article>
                  ))}</div>}
                </article>
              ))}
            </div>
          </section>

          <section className="result-section">
            <div className="result-heading">
              <div><p className="eyebrow">Tagging result</p><h2>{analysis.tags.length} investigation directions</h2></div>
              <span>Tags route questions; they do not declare causes.</span>
            </div>
            <div className="tag-grid">
              {analysis.tags.map((tag) => (
                <article className="tag-card" key={tag.id}>
                  <span className="confidence">{Math.round(tag.confidence * 100)}%</span>
                  <h3>{tag.label}</h3>
                  <p>{tag.rationale}</p>
                  <details><summary>Evidence from report</summary>
                    <ul>{tag.evidence.map((item) => <li key={item}>{item}</li>)}</ul>
                  </details>
                </article>
              ))}
            </div>
          </section>

          <section className="result-section">
            <div className="result-heading">
              <div><p className="eyebrow">Specialist workspaces</p><h2>Separate, evolving knowledge bases</h2></div>
              <span>The answer-fetching layer can search across all of them.</span>
            </div>
            <div className="knowledge-grid">
              {analysis.specialistKnowledgeBases.map((knowledge) => (
                <details className="knowledge-card" key={knowledge.tagId}>
                  <summary><span><strong>{knowledge.label}</strong><small>{knowledge.findings.length} findings · {knowledge.questionIds.length} questions</small></span><b>+</b></summary>
                  <p><small>Specialist proposal summary — consult reviewed findings below.</small><br />{knowledge.summary}</p>
                  <ul>{knowledge.findings.map((finding) => <li key={finding.id}><span className={`evidence-status ${finding.status}`}>{finding.status}</span>{finding.statement}</li>)}</ul>
                  {knowledge.handoffs.length > 0 && <p className="handoff-note">Handoffs: {knowledge.handoffs.map((handoff) => `${tagLabel(handoff.tagId)} — ${handoff.reason}`).join(' · ')}</p>}
                </details>
              ))}
            </div>
          </section>

          <section className="result-section">
            <div className="result-heading">
              <div><p className="eyebrow">Open investigation</p><h2>Questions for this snapshot</h2></div>
              <span>Any answer creates only this model’s next immutable version.</span>
            </div>
            {Object.entries(grouped).map(([tagId, questions]) => (
              <div className="question-group" key={tagId}>
                <div className="question-group-heading">
                  <span>{tagId === 'baseline' ? 'Step 0 · baseline context' : TAG_LABELS[tagId as TagId]}</span>
                  <span>{questions.length} questions</span>
                </div>
                {questions.map((question) => (
                  <QuestionCard key={question.id} question={question} trackId={track.id}
                    existingAnswer={answerMap.get(question.id)}
                    onSaved={async () => { await load(true); }} />
                ))}
              </div>
            ))}
          </section>

          <section className="result-section">
            <div className="result-heading">
              <div><p className="eyebrow">Evidence ledger</p><h2>{analysis.evidenceClaims.length} claims · {analysis.conflicts.length} contradictions</h2></div>
              <span>Observation, record, testimony, interpretation, and assumption remain distinguishable.</span>
            </div>
            {analysis.conflicts.length > 0 && <div className="conflict-list">{analysis.conflicts.map((conflict) => <article key={conflict.id}><strong>{conflict.summary}</strong><p>{conflict.resolutionNeeded}</p><span>{conflict.status}</span></article>)}</div>}
            <div className="claim-grid">{analysis.evidenceClaims.map((claim) => <article key={claim.id}><div><span>{claim.kind.replaceAll('-', ' ')}</span><b className={`evidence-status ${claim.status}`}>{claim.review ? claim.status : 'not reviewed'}</b></div><p>{claim.text}</p><small>{claim.sourceIds.length ? `Sources: ${claim.sourceIds.join(', ')}` : 'Source still required'}</small>
              {claim.review && <details><summary>Evidence review: {claim.review.verdict}</summary><p>{claim.review.reason}</p>{claim.review.citations.map((citation, index) => <blockquote key={index}><p>{citation.excerpt}</p><small>{citation.label} · {citation.sourceId}</small></blockquote>)}</details>}
            </article>)}</div>
          </section>

          <section className="result-section causal-section">
            <div className="result-heading">
              <div><p className="eyebrow">Causal board · {analysis.causalBoard.maturity}</p><h2>From reported event toward testable causes</h2></div>
              <span>Chronology is not treated as causation without supporting evidence.</span>
            </div>
            <CausalCanvas board={analysis.causalBoard} trackId={track.id} versionNumber={version.number}
              decisions={analysis.humanDecisions || []} onReviewed={async () => { await load(true); }} />
            <div className="causal-links">
              <h3>Proposed and supported links</h3>
              {analysis.causalBoard.edges.length === 0 && <p>No causal link has earned a place yet.</p>}
              {analysis.causalBoard.edges.map((edge) => {
                const from = analysis.causalBoard.nodes.find((node) => node.id === edge.from)?.label || edge.from;
                const to = analysis.causalBoard.nodes.find((node) => node.id === edge.to)?.label || edge.to;
                return <article key={edge.id}><strong>{from}</strong><span>{edge.type.replaceAll('-', ' ')} →</span><strong>{to}</strong><p>{edge.rationale}</p><small>Counterfactual: {edge.counterfactual}</small><small>Alternative: {edge.competingExplanation}</small><small>Evidence gap: {edge.evidenceGap}</small></article>;
              })}
            </div>
            {analysis.causalBoard.verificationFindings.length > 0 && <div className="verification-list"><h3>Verification findings</h3>{analysis.causalBoard.verificationFindings.map((finding) => <article key={finding.id}><span>{finding.severity}</span><strong>{finding.issue}</strong><p>{finding.evidenceNeeded}</p></article>)}</div>}
          </section>

          {analysis.correctiveActions.length > 0 && <section className="result-section"><div className="result-heading"><div><p className="eyebrow">Corrective action development</p><h2>Actions tied to causal findings</h2></div></div><div className="action-grid">{analysis.correctiveActions.map((action) => <article key={action.id}><span>{action.type} · {action.status}</span><h3>{action.title}</h3><p>{action.description}</p><dl><dt>Owner role</dt><dd>{action.ownerRole}</dd><dt>Completion evidence</dt><dd>{action.completionEvidence}</dd><dt>Effectiveness check</dt><dd>{action.effectivenessCheck}</dd></dl>{action.status !== 'accepted' && <button className="button save-button" type="button" onClick={() => reviewCorrectiveAction(action.id)}>Approve action</button>}</article>)}</div></section>}

          <section className="result-section two-column-details">
            <details className="audit-panel">
              <summary>
                <span><strong>Skipped / covered questions</strong><small>Question broker record</small></span>
                <b>{analysis.skippedQuestions.length}</b>
              </summary>
              <div className="audit-content">
                {analysis.skippedQuestions.length === 0 && <p>No overlapping questions were suppressed.</p>}
                {analysis.skippedQuestions.map((item) => (
                  <article key={item.id}>
                    <span>{tagLabel(item.proposedBy)} proposed</span>
                    <h3>{item.text}</h3>
                    <p>{item.reason}</p>
                    <small>Covered by {tagLabel(item.coveredByTagId)}</small>
                  </article>
                ))}
              </div>
            </details>
            <details className="audit-panel">
              <summary>
                <span><strong>Stage checkpoints</strong><small>Persisted outputs from this model run</small></span>
                <b>{(track.checkpoints || []).filter((item) => item.targetVersion === version.number).length}</b>
              </summary>
              <div className="audit-content">
                {(track.checkpoints || []).filter((item) => item.targetVersion === version.number).map((item) => (
                  <article key={item.id}>
                    <span>{item.status} · {formatTime(item.createdAt)}</span>
                    <h3>{item.sequence}. {tagLabel(item.stage)}</h3>
                    <details><summary>Inspect saved output</summary><pre>{JSON.stringify(item.payload, null, 2)}</pre></details>
                  </article>
                ))}
              </div>
            </details>
            <details className="audit-panel">
              <summary>
                <span><strong>Decision trace</strong><small>Inspectable rationale, not private chain-of-thought</small></span>
                <b>{analysis.trace.length}</b>
              </summary>
              <div className="audit-content">
                {analysis.trace.map((entry) => (
                  <article key={entry.id}>
                    <span>{entry.stage} · {Math.round(entry.confidence * 100)}% confidence</span>
                    <h3>{entry.summary}</h3>
                    <p>Prompt {entry.promptVersion} · {entry.engine} · {entry.durationMs} ms</p>
                    {entry.evidence.length > 0 && <small>Basis: {entry.evidence.join(' · ')}</small>}
                  </article>
                ))}
              </div>
            </details>
            <details className="audit-panel">
              <summary><span><strong>Human review record</strong><small>Accepted, rejected, closed, and approved findings</small></span><b>{(analysis.humanDecisions || []).length}</b></summary>
              <div className="audit-content">{(analysis.humanDecisions || []).length === 0 && <p>No human decisions recorded in this version.</p>}{(analysis.humanDecisions || []).map((decision) => <article key={decision.id}><span>{decision.actor} · {formatTime(decision.createdAt)}</span><h3>{decision.action.replaceAll('-', ' ')} · {decision.targetType.replaceAll('-', ' ')}</h3><p>{decision.notes || decision.targetId}</p></article>)}</div>
            </details>
          </section>
        </section>
      </div>
    </main>
  );
}
