'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import type { ModelDescriptor } from '@/src/domain/types';

export default function ModelRegistryPage() {
  const [models, setModels] = useState<ModelDescriptor[]>([]);
  const [tag, setTag] = useState('');
  const [ollamaUrl, setOllamaUrl] = useState('');
  const [apiConfigured, setApiConfigured] = useState(false);
  const [message, setMessage] = useState('');
  const [pulling, setPulling] = useState(false);

  const refresh = useCallback(async () => {
    const response = await fetch('/api/models', { cache: 'no-store' });
    const data = await response.json() as {
      models: ModelDescriptor[];
      ollamaUrl: string;
      apiProviderConfigured: boolean;
    };
    setModels(data.models);
    setOllamaUrl(data.ollamaUrl);
    setApiConfigured(data.apiProviderConfigured);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { void refresh(); }, 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  async function pull() {
    if (!tag.trim()) return;
    setPulling(true);
    setMessage('Asking Ollama to pull ' + tag.trim() + '…');
    const response = await fetch('/api/models', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ tag: tag.trim() }),
    });
    const result = await response.json() as { error?: string };
    setMessage(response.ok ? 'Model pulled successfully.' : result.error || 'Pull failed.');
    setPulling(false);
    if (response.ok) {
      setTag('');
      await refresh();
    }
  }

  return (
    <main className="library-shell">
      <header className="dashboard-header">
        <Link className="brand" href="/"><span className="brand-mark">R</span><span>RCA Fieldwork</span></Link>
        <p>Model registry</p>
        <Link className="button ghost-button" href="/">Done</Link>
      </header>
      <section className="settings-content">
        <div className="library-heading">
          <div><p className="eyebrow">Provider-neutral registry</p><h1>Models enter through one boundary.</h1></div>
          <p>Credentials are environment configuration and are never written to investigation history.</p>
        </div>
        <div className="settings-grid">
          <section className="settings-card">
            <p className="eyebrow">Available now</p>
            <h2>Detected models</h2>
            <div className="registry-list">
              {models.map((model) => (
                <div key={model.id}><span className="status-dot" /><span><strong>{model.name}</strong><small>{model.detail}</small></span><b>{model.available ? 'ready' : 'offline'}</b></div>
              ))}
            </div>
          </section>
          <section className="settings-card dark">
            <p className="eyebrow">Ollama</p>
            <h2>Pull by model tag</h2>
            <p>Connected endpoint: <code>{ollamaUrl || 'checking…'}</code></p>
            <div className="inline-form">
              <input value={tag} onChange={(event) => setTag(event.target.value)}
                placeholder="e.g. qwen3:8b" />
              <button className="button primary-button compact" onClick={pull}
                disabled={pulling || !tag.trim()} type="button">
                {pulling ? 'Pulling…' : 'Pull'}
              </button>
            </div>
            {message && <p className="form-message">{message}</p>}
          </section>
          <section className="settings-card">
            <p className="eyebrow">Closed-source / hosted</p>
            <h2>{apiConfigured ? 'API provider configured' : 'Ready for API configuration'}</h2>
            <p>Set <code>MODEL_PROVIDER_BASE_URL</code> and <code>MODEL_PROVIDER_API_KEY</code>
              in the ignored local environment file. Provider keys never enter D1, R2, prompts, or traces.</p>
          </section>
        </div>
      </section>
    </main>
  );
}
