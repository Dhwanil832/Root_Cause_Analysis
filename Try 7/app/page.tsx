'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import type { ModelDescriptor } from '@/src/domain/types';

export default function Home() {
  const [incident, setIncident] = useState('');
  const [starterDocuments, setStarterDocuments] = useState<File[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [showModelPanel, setShowModelPanel] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');
  const [models, setModels] = useState<ModelDescriptor[]>([]);
  const canStart = incident.trim().length >= 30 && selected.length > 0;
  const selectedLabel = useMemo(() => selected.length === 1
    ? '1 independent investigation'
    : selected.length + ' independent investigations', [selected]);

  useEffect(() => {
    fetch('/api/models', { cache: 'no-store' })
      .then((response) => response.json() as Promise<{ models?: ModelDescriptor[] }>)
      .then((payload) => {
        setModels(payload.models||[]);
      })
      .catch(() => {
        setError('Model discovery is unavailable. Start Ollama or configure an API provider.');
      });
  }, []);

  useEffect(() => {
    type ModelContext = { registerTool: (tool: unknown, options?: { signal?: AbortSignal }) => void | Promise<void> };
    const context = (document as Document & { modelContext?: ModelContext }).modelContext;
    if (!context?.registerTool) return;
    const lifecycle = new AbortController();
    void Promise.resolve(context.registerTool({
      name: 'create_rca_investigation',
      title: 'Create RCA investigation',
      description: 'Create a new root-cause investigation from an incident description using one or more available model IDs. This creates preserved model tracks and navigates to the resulting dashboard.',
      inputSchema: {
        type: 'object',
        properties: {
          description: { type: 'string', minLength: 30 },
          modelIds: { type: 'array', items: { type: 'string' }, minItems: 1 },
        },
        required: ['description', 'modelIds'],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: false, untrustedContentHint: true },
      async execute(input: unknown) {
        const value = input as { description?: unknown; modelIds?: unknown };
        if (typeof value.description !== 'string' || value.description.trim().length < 30 ||
          !Array.isArray(value.modelIds) || !value.modelIds.every((id) => typeof id === 'string')) {
          throw new Error('A meaningful description and at least one model ID are required.');
        }
        const response = await fetch('/api/incidents', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ description: value.description.trim(), modelIds: value.modelIds, deferAnalysis: true }),
        });
        const payload = await response.json() as { id?: string; error?: string };
        if (!response.ok || !payload.id) throw new Error(payload.error || 'Unable to create the investigation.');
        window.location.href = `/incident/${payload.id}?start=1`;
        return { incidentId: payload.id, status: 'created' };
      },
    }, { signal: lifecycle.signal })).catch(() => {
      // The visible workflow remains fully available when WebMCP is unsupported.
    });
    return () => lifecycle.abort();
  }, []);

  function toggleModel(id: string) {
    if (!models.find((model) => model.id === id)?.available) return;
    setSelected((current) => current.includes(id)
      ? current.filter((modelId) => modelId !== id)
      : [...current, id]);
  }

  async function startInvestigation() {
    if (!canStart) return;
    setStarting(true);
    setError('');
    try {
      const form = new FormData();
      form.append('description', incident.trim());
      form.append('modelIds', JSON.stringify(selected));
      form.append('deferAnalysis', 'true');
      for (const file of starterDocuments) form.append('files', file);
      const response = await fetch('/api/incidents', { method: 'POST', body: form });
      const payload = await response.json() as { id?: string; error?: string };
      if (!response.ok || !payload.id) throw new Error(payload.error || 'Unable to create the investigation.');
      window.location.href = `/incident/${payload.id}?start=1`;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to create the investigation.');
      setStarting(false);
    }
  }

  return (
    <main className="landing-shell">
      <header className="site-header">
        <Link className="brand" href="/" aria-label="RCA Fieldwork home">
          <span className="brand-mark" aria-hidden="true">R</span>
          <span>RCA Fieldwork <small className="brand-edition">Try 7</small></span>
        </Link>
        <nav className="header-actions" aria-label="Primary navigation">
          <span className="local-badge"><span className="status-dot" />Local workspace</span>
          <Link className="button ghost-button" href="/history">Run history</Link>
        </nav>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Root-cause investigation workspace</p>
          <h1>Build the case from evidence.</h1>
          <p className="lede">
            Start with the account and available records. Each model develops its own
            specialist knowledge, questions, evidence map, and causal board.
          </p>
        </div>

        <div className="workbench">
          <div className="input-card">
            <label htmlFor="incident">
              Incident description
              <span>Original account · never overwritten</span>
            </label>
            <textarea
              id="incident"
              value={incident}
              onChange={(event) => setIncident(event.target.value)}
              placeholder="Paste the incident description, field report, or first known account here…"
              rows={12}
            />
            <div className="input-foot">
              <span>{incident.trim().length.toLocaleString()} characters</span>
              <span>The initial map will identify terms and conditions that need clarification</span>
            </div>
            <div className="starter-documents">
              <div>
                <strong>Incident starter documents</strong>
                <span>Reports, photographs, drawings, work orders, or other records available at intake</span>
              </div>
              <label className="document-picker">
                <input type="file" multiple onChange={(event) => setStarterDocuments(Array.from(event.target.files || []))} />
                {starterDocuments.length ? `${starterDocuments.length} selected` : 'Choose files'}
              </label>
              {starterDocuments.length > 0 && (
                <ul>{starterDocuments.map((file) => <li key={file.name + file.size}>{file.name}</li>)}</ul>
              )}
            </div>
          </div>

          <aside className="model-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Investigation panel</p>
                <h2>Choose models</h2>
              </div>
              <button className="text-button" type="button"
                onClick={() => setShowModelPanel((value) => !value)}>
                {showModelPanel ? 'Close' : 'Add model'}
              </button>
            </div>

            <div className="model-list">
              {!models.length&&<p>Looking for installed Ollama models. If none appear, start Ollama or configure a provider in the model registry.</p>}
              {models.map((model) => {
                const checked = selected.includes(model.id);
                return (
                  <button className={'model-option' + (checked ? ' selected' : '')}
                    key={model.id} onClick={() => toggleModel(model.id)}
                    type="button" aria-pressed={checked} disabled={!model.available}>
                    <span className="check" aria-hidden="true">{checked ? '✓' : ''}</span>
                    <span className="model-copy">
                      <strong>{model.name}</strong>
                      <small>{model.detail}</small>
                    </span>
                    <span className="model-status">{model.available ? 'Ready' : 'Offline'}</span>
                  </button>
                );
              })}
            </div>

            {showModelPanel && (
              <div className="add-panel">
                <strong>Connect another model</strong>
                <p>Ollama pull tags and API-backed providers are configured from the
                  model registry. Credentials stay out of run history.</p>
                <Link href="/settings/models">Open model registry →</Link>
              </div>
            )}

            <div className="independence-note">
              <span aria-hidden="true">↗</span>
              <p><strong>Independent by design.</strong> Answers in one model create a
                new version only for that model.</p>
            </div>

            <div className="reference-note">
              <div><strong>Default reference library</strong><span>Plant layouts, handbooks, and approved standards</span></div>
              <Link href="/references">Manage →</Link>
            </div>

            <button className="button primary-button" type="button"
              disabled={!canStart || starting} onClick={startInvestigation}>
              {starting ? 'Building independent tracks…' : `Start ${selectedLabel}`}<span aria-hidden="true">→</span>
            </button>
            {error && <p className="form-error">{error}</p>}
            {!canStart && (
              <p className="start-hint">Add a meaningful incident description and select a model.</p>
            )}
          </aside>
        </div>
      </section>

      <footer className="landing-footer">
        <p>Evidence → initial map → targeted expertise → concrete evidence directions</p>
        <p>Every decision remains inspectable.</p>
      </footer>
    </main>
  );
}
