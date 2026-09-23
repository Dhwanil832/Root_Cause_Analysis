'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import type { ModelDescriptor } from '@/src/domain/types';

const STARTER_MODELS = [
  { id: 'demo-field-analyst', name: 'Field Analyst', detail: 'Built-in deterministic preview', status: 'Ready' },
  { id: 'ollama-qwen3', name: 'Qwen 3', detail: 'Ollama · local', status: 'Check Ollama' },
  { id: 'ollama-llama33', name: 'Llama 3.3', detail: 'Ollama · local', status: 'Check Ollama' },
];

export default function Home() {
  const [incident, setIncident] = useState('');
  const [selected, setSelected] = useState<string[]>(['demo-field-analyst']);
  const [showModelPanel, setShowModelPanel] = useState(false);
  const [models, setModels] = useState<ModelDescriptor[]>(
    STARTER_MODELS.map((model) => ({
      ...model,
      provider: model.id.startsWith('ollama') ? 'ollama' : 'builtin',
      available: model.id === 'demo-field-analyst',
    })) as ModelDescriptor[],
  );
  const canStart = incident.trim().length >= 30 && selected.length > 0;
  const selectedLabel = useMemo(() => selected.length === 1
    ? '1 independent investigation'
    : selected.length + ' independent investigations', [selected]);

  useEffect(() => {
    fetch('/api/models', { cache: 'no-store' })
      .then((response) => response.json())
      .then((payload: { models?: ModelDescriptor[] }) => {
        if (payload.models?.length) setModels(payload.models);
      })
      .catch(() => {
        // Keep the built-in registry visible when Ollama discovery is unavailable.
      });
  }, []);

  function toggleModel(id: string) {
    setSelected((current) => current.includes(id)
      ? current.filter((modelId) => modelId !== id)
      : [...current, id]);
  }

  function startInvestigation() {
    if (!canStart) return;
    window.localStorage.setItem('rca:draft', JSON.stringify({
      incident: incident.trim(),
      selected,
    }));
    window.location.href = '/new';
  }

  return (
    <main className="landing-shell">
      <header className="site-header">
        <Link className="brand" href="/" aria-label="RCA Fieldwork home">
          <span className="brand-mark" aria-hidden="true">R</span>
          <span>RCA Fieldwork</span>
        </Link>
        <nav className="header-actions" aria-label="Primary navigation">
          <span className="local-badge"><span className="status-dot" />Local workspace</span>
          <Link className="button ghost-button" href="/history">Run history</Link>
        </nav>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Root-cause investigation workspace</p>
          <h1>Start with what happened.</h1>
          <p className="lede">
            Give each model the same incident. Let every one build its own evidence,
            tags, questions, and version history—without cross-talk.
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
              <span>Step 0 will identify terms that need context</span>
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
              {models.map((model) => {
                const checked = selected.includes(model.id);
                return (
                  <button className={'model-option' + (checked ? ' selected' : '')}
                    key={model.id} onClick={() => toggleModel(model.id)}
                    type="button" aria-pressed={checked}>
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

            <button className="button primary-button" type="button"
              disabled={!canStart} onClick={startInvestigation}>
              Start {selectedLabel}<span aria-hidden="true">→</span>
            </button>
            {!canStart && (
              <p className="start-hint">Add a meaningful incident description and select a model.</p>
            )}
          </aside>
        </div>
      </section>

      <footer className="landing-footer">
        <p>Context → tags → specialist questions → brokered investigation</p>
        <p>Every decision remains inspectable.</p>
      </footer>
    </main>
  );
}
