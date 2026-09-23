'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import type {
  IncidentRecord, InvestigationQuestion, TagId, TrackRecord, VersionRecord,
} from '@/src/domain/types';
import { TAG_LABELS } from '@/src/domain/tag-catalog';

function formatTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  }).format(new Date(value));
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

  if (error) {
    return <main className="center-page"><div className="processing-card"><h1>{error}</h1><Link href="/history">Return to history</Link></div></main>;
  }
  if (!incident || !track || !version) {
    return <main className="center-page"><div className="processing-card"><p>Loading investigation…</p></div></main>;
  }

  const analysis = version.analysis;
  const answerMap = new Map(analysis.answers.map((answer) => [answer.questionId, answer.text]));
  const allQuestions = [...analysis.baselineQuestions, ...analysis.questions];
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
            <span>{analysis.answers.length} preserved answers</span>
          </div>

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
                    <span>{TAG_LABELS[item.proposedBy]} proposed</span>
                    <h3>{item.text}</h3>
                    <p>{item.reason}</p>
                    <small>Covered by {item.coveredByTagId === 'baseline' ? 'Step 0' : TAG_LABELS[item.coveredByTagId]}</small>
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
          </section>
        </section>
      </div>
    </main>
  );
}
