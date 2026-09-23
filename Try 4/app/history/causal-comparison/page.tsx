'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { CausalCanvas } from '@/app/incident/causal-canvas';
import type { CausalBoard } from '@/src/domain/types';
import comparison from '@/src/history/featured-comparison.json';
import './comparison.css';

interface SavedBoard {
  number: number;
  label: string;
  subtitle: string;
  createdAt: string;
  status: string;
  sourcePath: string;
  sourceSha256: string;
  sourceRecordId: string;
  board: CausalBoard;
}
const noReview = async () => {};

export default function CausalComparisonPage() {
  const [versions, setVersions] = useState<SavedBoard[]>([]);
  const [view, setView] = useState<'both' | 1 | 2>('both');
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    fetch(comparison.dataUrl, { signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error('Unable to load the preserved boards.');
        const saved = await response.json() as { versions: SavedBoard[] };
        if (saved.versions?.length !== 2 || saved.versions.some((v, i) => v.number !== i + 1 || !Array.isArray(v.board?.nodes) || !Array.isArray(v.board?.edges))) {
          throw new Error('The preserved comparison is missing V1 or V2.');
        }
        setVersions(saved.versions);
      })
      .catch(caught => { if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : 'Unable to load boards.'); });
    return () => controller.abort();
  }, []);

  return (
    <main className="comparison-shell">
      <header className="dashboard-header">
        <Link className="brand" href="/"><span className="brand-mark">R</span><span>RCA Fieldwork · {comparison.app}</span></Link>
        <Link className="button compact" href="/history">Back to history</Link>
      </header>
      <section className="comparison-intro">
        <p className="eyebrow">Pinned incident · Preserved causal boards</p>
        <h1>{comparison.title}</h1>
        <p className="comparison-description">{comparison.description}</p>
        <p><strong>Model:</strong> {comparison.modelName}</p>
        <aside className="comparison-notice" role="note">{comparison.note} This comparison is read-only; no model runs or review decisions are triggered.</aside>
        <div className="comparison-links">
          <Link href={'/incident/' + comparison.originalIncidentId}>Open original investigation</Link>
          <a href={comparison.dataUrl} download>Download both saved boards (JSON)</a>
        </div>
        <nav className="comparison-controls" aria-label="Causal board versions">
          <button type="button" aria-pressed={view === 'both'} onClick={() => setView('both')}>Compare V1 + V2</button>
          <button type="button" aria-pressed={view === 1} onClick={() => setView(1)}>V1{comparison.kind === 'diagnostic-snapshots' ? ' · Before' : ''}</button>
          <button type="button" aria-pressed={view === 2} onClick={() => setView(2)}>V2{comparison.kind === 'diagnostic-snapshots' ? ' · After' : ''}</button>
        </nav>
        <p className="comparison-help">Drag nodes and use each board’s zoom controls. Scroll within a board to explore it; expand the full node text below to read every statement. Display layouts are separate for V1 and V2.</p>
      </section>
      {error && <p className="empty-state error-state" role="alert">{error}</p>}
      {!error && !versions.length && <p className="empty-state">Loading both saved causal boards…</p>}
      <div className={view === 'both' ? 'comparison-boards side-by-side' : 'comparison-boards'}>
        {versions.filter(v => view === 'both' || v.number === view).map(v => (
          <section className="comparison-board" key={v.number} aria-label={v.label}>
            <header className="comparison-board-heading">
              <h2>{v.label}</h2><p>{v.subtitle}</p>
              <p><strong>{v.board.nodes.length} nodes · {v.board.edges.length} connections</strong> · Saved status: {v.status}</p>
            </header>
            <CausalCanvas
              key={v.number}
              board={v.board}
              trackId={`archive:${comparison.app}:${comparison.originalTrackId}:v${v.number}`}
              versionNumber={v.number}
              decisions={[]}
              onReviewed={noReview}
              readOnly
              viewLabel={v.label}
            />
            <details className="comparison-node-text">
              <summary>Full node statements and evidence references ({v.board.nodes.length})</summary>
              {v.board.nodes.map(node => <article key={node.id}>
                <h3>{node.label}</h3>
                <p>{node.detail}</p>
                <p><strong>Type:</strong> {node.type} · <strong>Saved status:</strong> {node.status} · <strong>Verified:</strong> {node.verified ? 'yes' : 'no'}</p>
                <p><strong>Source references:</strong> {node.sourceIds.join(', ') || 'None recorded'}</p>
                <small>Node ID: {node.id}</small>
              </article>)}
            </details>
            <details className="comparison-provenance">
              <summary>Original snapshot provenance</summary>
              <p>Recorded: {v.createdAt}</p>
              <p>Source file: {v.sourcePath}</p>
              <p>Source record: {v.sourceRecordId}</p>
              <p>Source file SHA-256: {v.sourceSha256}</p>
              <p>Imported for display only. No board statements, connections, statuses or verification findings have been rewritten.</p>
            </details>
          </section>
        ))}
      </div>
    </main>
  );
}

