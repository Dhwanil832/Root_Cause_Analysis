'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

interface HistoryItem {
  id: string;
  title: string;
  description: string;
  createdAt: string;
  updatedAt: string;
  models: Array<{ name: string; latestVersion: number }>;
}

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/incidents', { cache: 'no-store' })
      .then(async (response) => {
        const payload = await response.json() as { incidents?: HistoryItem[]; error?: string };
        if (!response.ok) throw new Error(payload.error || 'Unable to load history.');
        setItems(payload.incidents || []);
      })
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Unable to load history.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="library-shell">
      <header className="dashboard-header">
        <Link className="brand" href="/"><span className="brand-mark">R</span><span>RCA Fieldwork</span></Link>
        <p>Preserved investigations</p>
        <Link className="button primary-button compact" href="/">New incident</Link>
      </header>
      <section className="library-content">
        <div className="library-heading">
          <div><p className="eyebrow">Run history</p><h1>Every investigation, intact.</h1></div>
          <p>Select an incident, then a model, then one of that model’s versions.</p>
        </div>
        {loading && <div className="empty-state">Loading preserved runs…</div>}
        {error && <div className="empty-state error-state">{error}</div>}
        {!loading && !error && items.length === 0 && (
          <div className="empty-state">
            <h2>No investigations yet</h2>
            <p>Your first incident will appear here after its independent model tracks are created.</p>
            <Link className="button primary-button compact" href="/">Start one</Link>
          </div>
        )}
        <div className="history-list">
          {items.map((item) => (
            <Link className="history-card" href={'/incident/' + item.id} key={item.id}>
              <div>
                <span>{new Date(item.updatedAt).toLocaleDateString()}</span>
                <h2>{item.title}</h2>
                <p>{item.description}</p>
              </div>
              <div className="history-models">
                {item.models.map((model) => (
                  <span key={model.name}>
                    <strong>{model.name}</strong>{' '}
                    {model.latestVersion > 0 ? `V${model.latestVersion}` : 'No completed version'}
                  </span>
                ))}
              </div>
              <b aria-hidden="true">→</b>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
