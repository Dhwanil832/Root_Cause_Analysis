'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import type { ModelDescriptor, ProviderConfig } from '@/src/domain/types';

const EMPTY_PROVIDER = {
  name: '', baseUrl: 'https://api.openai.com/v1', apiMode: 'responses' as ProviderConfig['apiMode'],
  models: '', apiKey: '',
};

export default function ModelRegistryPage() {
  const [models, setModels] = useState<ModelDescriptor[]>([]);
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [tag, setTag] = useState('');
  const [ollamaUrl, setOllamaUrl] = useState('');
  const [message, setMessage] = useState('');
  const [pulling, setPulling] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState('');
  const [providerForm, setProviderForm] = useState(EMPTY_PROVIDER);

  const refresh = useCallback(async () => {
    const [modelResponse, providerResponse] = await Promise.all([
      fetch('/api/models', { cache: 'no-store' }),
      fetch('/api/providers', { cache: 'no-store' }),
    ]);
    const modelData = await modelResponse.json() as { models: ModelDescriptor[]; ollamaUrl: string };
    const providerData = await providerResponse.json() as { providers?: ProviderConfig[]; error?: string };
    setModels(modelData.models || []);
    setOllamaUrl(modelData.ollamaUrl || '');
    setProviders(providerData.providers || []);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { void refresh().catch(() => setMessage('Unable to load the model registry.')); }, 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  async function pull() {
    if (!tag.trim()) return;
    setPulling(true);
    setMessage(`Asking Ollama to pull ${tag.trim()}…`);
    const response = await fetch('/api/models', {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ tag: tag.trim() }),
    });
    const result = await response.json() as { error?: string };
    setMessage(response.ok ? 'Model pulled successfully.' : result.error || 'Pull failed.');
    setPulling(false);
    if (response.ok) { setTag(''); await refresh(); }
  }

  async function saveProvider() {
    setSaving(true);
    setMessage('');
    try {
      const response = await fetch('/api/providers', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          id: editingId || undefined,
          name: providerForm.name,
          baseUrl: providerForm.baseUrl,
          apiMode: providerForm.apiMode,
          modelIds: providerForm.models.split(/[\n,]/).map((value) => value.trim()).filter(Boolean),
          apiKey: providerForm.apiKey || undefined,
          enabled: true,
        }),
      });
      const result = await response.json() as { error?: string };
      if (!response.ok) throw new Error(result.error || 'Unable to save provider.');
      setProviderForm(EMPTY_PROVIDER);
      setEditingId('');
      setMessage('Hosted provider saved. Its key is encrypted and is never returned to the browser.');
      await refresh();
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : 'Unable to save provider.');
    } finally {
      setSaving(false);
    }
  }

  function editProvider(provider: ProviderConfig) {
    setEditingId(provider.id);
    setProviderForm({
      name: provider.name, baseUrl: provider.baseUrl, apiMode: provider.apiMode,
      models: provider.modelIds.join('\n'), apiKey: '',
    });
    setMessage('Leave the API key blank to keep the current encrypted credential.');
  }

  async function providerAction(provider: ProviderConfig, action: 'test' | 'toggle' | 'delete') {
    setMessage(action === 'test' ? `Testing ${provider.name}…` : 'Updating provider…');
    const options = action === 'delete'
      ? { method: 'DELETE', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ id: provider.id }) }
      : { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(action === 'test'
          ? { action: 'test', id: provider.id }
          : { ...provider, modelIds: provider.modelIds, enabled: !provider.enabled }) };
    const response = await fetch('/api/providers', options);
    const result = await response.json() as { error?: string };
    setMessage(response.ok ? (action === 'test' ? 'Provider connection succeeded.' : 'Provider updated.') : result.error || 'Provider action failed.');
    if (response.ok) await refresh();
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
          <div><p className="eyebrow">Provider-neutral registry</p><h1>Choose where each investigation runs.</h1></div>
          <p>Local and hosted models enter through the same validated stage contracts. Credentials stay outside investigation history.</p>
        </div>
        <div className="settings-grid provider-settings-grid">
          <section className="settings-card">
            <p className="eyebrow">Available now</p><h2>Detected models</h2>
            <div className="registry-list">
              {models.map((model) => <div key={model.id}><span className="status-dot" /><span><strong>{model.name}</strong><small>{model.detail}</small></span><b>{model.available ? 'ready' : 'offline'}</b></div>)}
            </div>
          </section>
          <section className="settings-card dark">
            <p className="eyebrow">Ollama</p><h2>Pull by model tag</h2>
            <p>Connected endpoint: <code>{ollamaUrl || 'checking…'}</code></p>
            <div className="inline-form"><input value={tag} onChange={(event) => setTag(event.target.value)} placeholder="e.g. qwen3.5" /><button className="button primary-button compact" onClick={pull} disabled={pulling || !tag.trim()} type="button">{pulling ? 'Pulling…' : 'Pull'}</button></div>
          </section>
          <section className="settings-card provider-form-card">
            <p className="eyebrow">Hosted provider vault</p><h2>{editingId ? 'Edit provider' : 'Add API provider'}</h2>
            <div className="provider-form">
              <label>Provider name<input value={providerForm.name} onChange={(event) => setProviderForm({ ...providerForm, name: event.target.value })} placeholder="OpenAI production" /></label>
              <label>API base URL<input value={providerForm.baseUrl} onChange={(event) => setProviderForm({ ...providerForm, baseUrl: event.target.value })} /></label>
              <label>API protocol<select value={providerForm.apiMode} onChange={(event) => setProviderForm({ ...providerForm, apiMode: event.target.value as ProviderConfig['apiMode'] })}><option value="responses">Responses API</option><option value="chat-completions">OpenAI-compatible Chat Completions</option></select></label>
              <label>Model IDs<textarea rows={4} value={providerForm.models} onChange={(event) => setProviderForm({ ...providerForm, models: event.target.value })} placeholder={'One per line, for example:\ngpt-5.5'} /></label>
              <label>API key<input type="password" autoComplete="new-password" value={providerForm.apiKey} onChange={(event) => setProviderForm({ ...providerForm, apiKey: event.target.value })} placeholder={editingId ? 'Leave blank to keep current key' : 'Stored encrypted'} /></label>
              <div className="provider-form-actions"><button className="button primary-button compact" type="button" onClick={saveProvider} disabled={saving}>{saving ? 'Encrypting…' : editingId ? 'Save changes' : 'Add provider'}</button>{editingId && <button className="button ghost-button" type="button" onClick={() => { setEditingId(''); setProviderForm(EMPTY_PROVIDER); }}>Cancel</button>}</div>
            </div>
          </section>
          <section className="settings-card provider-list-card">
            <p className="eyebrow">Saved hosted providers</p><h2>{providers.length} configured</h2>
            {providers.length === 0 && <p>No hosted providers have been added.</p>}
            <div className="provider-list">{providers.map((provider) => <article key={provider.id}><div><strong>{provider.name}</strong><span>{provider.enabled ? 'enabled' : 'disabled'} · key {provider.keyHint}</span></div><p>{provider.apiMode} · {provider.modelIds.join(', ')}</p><small>{provider.baseUrl}</small><div><button type="button" onClick={() => editProvider(provider)}>Edit</button><button type="button" onClick={() => providerAction(provider, 'test')}>Test</button><button type="button" onClick={() => providerAction(provider, 'toggle')}>{provider.enabled ? 'Disable' : 'Enable'}</button><button type="button" onClick={() => providerAction(provider, 'delete')}>Delete</button></div></article>)}</div>
          </section>
        </div>
        {message && <p className="settings-message">{message}</p>}
      </section>
    </main>
  );
}
