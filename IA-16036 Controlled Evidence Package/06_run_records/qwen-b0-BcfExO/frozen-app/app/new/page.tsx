'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

export default function NewInvestigationPage() {
  const once = useRef(false);
  const [message, setMessage] = useState('Creating independent model tracks…');
  const [error, setError] = useState('');

  useEffect(() => {
    if (once.current) return;
    once.current = true;
    const raw = window.localStorage.getItem('rca:draft');
    if (!raw) {
      queueMicrotask(() => setError('No incident draft was found.'));
      return;
    }
    const draft = JSON.parse(raw) as { incident?: string; selected?: string[] };
    fetch('/api/incidents', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ description: draft.incident, modelIds: draft.selected }),
    })
      .then(async (response) => {
        const result = await response.json() as { id?: string; error?: string };
        if (!response.ok || !result.id) throw new Error(result.error || 'Unable to start.');
        window.localStorage.removeItem('rca:draft');
        setMessage('Opening the investigation dashboard…');
        window.location.replace('/incident/' + result.id);
      })
      .catch((caught: unknown) => {
        setError(caught instanceof Error ? caught.message : 'Unable to start the investigation.');
      });
  }, []);

  return (
    <main className="center-page">
      <div className="processing-card">
        <span className="processing-mark">R</span>
        {!error ? (
          <>
            <p className="eyebrow">Version 1</p>
            <h1>{message}</h1>
            <div className="progress-line"><span /></div>
            <p>Step 0 → tagging → specialists → question broker</p>
          </>
        ) : (
          <>
            <p className="eyebrow">Could not begin</p>
            <h1>{error}</h1>
            <Link className="button primary-button" href="/">Return to the start</Link>
          </>
        )}
      </div>
    </main>
  );
}
