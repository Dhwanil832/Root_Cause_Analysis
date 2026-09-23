'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import type { DocumentRecord } from '@/src/domain/types';

export default function ReferenceLibraryPage() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [plant, setPlant] = useState('General');
  const [revision, setRevision] = useState('1');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function load() {
    const response = await fetch('/api/references', { cache: 'no-store' });
    const payload = await response.json() as { documents?: DocumentRecord[]; error?: string };
    if (!response.ok) throw new Error(payload.error || 'Unable to load references.');
    setDocuments(payload.documents || []);
  }

  useEffect(() => {
    let cancelled = false;
    fetch('/api/references', { cache: 'no-store' })
      .then((response) => response.json().then((payload) => ({ response, payload: payload as { documents?: DocumentRecord[]; error?: string } })))
      .then(({ response, payload }) => {
        if (!response.ok) throw new Error(payload.error || 'Unable to load references.');
        if (!cancelled) setDocuments(payload.documents || []);
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(caught instanceof Error ? caught.message : 'Unable to load references.');
      });
    return () => { cancelled = true; };
  }, []);

  async function upload() {
    if (!file) return;
    setSaving(true);
    setError('');
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('title', title.trim() || file.name);
      form.append('plant', plant.trim() || 'General');
      form.append('revision', revision.trim() || '1');
      const response = await fetch('/api/references', { method: 'POST', body: form });
      const payload = await response.json() as { error?: string };
      if (!response.ok) throw new Error(payload.error || 'Unable to upload the reference.');
      setFile(null);
      setTitle('');
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to upload the reference.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="library-shell">
      <header className="dashboard-header">
        <Link className="brand" href="/"><span className="brand-mark">R</span><span>RCA Fieldwork <small className="brand-edition">Try 5</small></span></Link>
        <div className="breadcrumb"><Link href="/">New incident</Link><span>/</span><span>Reference library</span></div>
        <Link className="button ghost-button" href="/history">Run history</Link>
      </header>

      <section className="library-hero">
        <p className="eyebrow">Default investigation context</p>
        <h1>Reference library</h1>
        <p>Plant layouts, safety handbooks, approved procedures, and standing technical references are versioned here. Every new model track receives its own preserved attachment to the current library.</p>
      </section>

      <section className="library-grid">
        <article className="library-upload">
          <p className="eyebrow">Add reference</p>
          <label>Document title<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Defaults to the file name" /></label>
          <div className="library-fields">
            <label>Plant or scope<input value={plant} onChange={(event) => setPlant(event.target.value)} /></label>
            <label>Revision<input value={revision} onChange={(event) => setRevision(event.target.value)} /></label>
          </div>
          <label className="document-picker library-picker"><input type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} />{file ? file.name : 'Choose a document'}</label>
          <button className="button primary-button" type="button" disabled={!file || saving} onClick={upload}>{saving ? 'Extracting and preserving…' : 'Add to library'}</button>
          {error && <p className="form-error">{error}</p>}
        </article>

        <section className="library-list">
          <div className="result-heading"><div><p className="eyebrow">Available to future tracks</p><h2>{documents.length} reference documents</h2></div></div>
          {documents.length === 0 && <div className="empty-panel"><h3>No default references yet</h3><p>Add a plant layout, employee safety handbook, or another controlled reference.</p></div>}
          {documents.map((document) => (
            <article className="document-row" key={document.id}>
              <div><strong>{document.title}</strong><span>{document.fileName} · {Math.ceil(document.size / 1024).toLocaleString()} KB</span></div>
              <div><span>{document.plant}</span><span>Rev {document.revision}</span></div>
              <span className={`extraction-state ${document.extractionStatus}`}>{document.extractionStatus}</span>
            </article>
          ))}
        </section>
      </section>
    </main>
  );
}
