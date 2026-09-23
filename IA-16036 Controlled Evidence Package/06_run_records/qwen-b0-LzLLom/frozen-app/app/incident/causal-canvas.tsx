'use client';

import { useEffect, useMemo, useState } from 'react';
import type { CausalBoard, CausalNode, HumanDecision } from '@/src/domain/types';

type Position = { x: number; y: number };

const REVIEWABLE = new Set(['condition', 'change', 'barrier', 'direct-cause', 'contributing-cause', 'root-cause-candidate']);

function initialPositions(nodes: CausalNode[]) {
  const columns: Record<string, number> = {
    evidence: 20, unknown: 20, condition: 280, change: 280, barrier: 550,
    'human-decision-action': 550, 'direct-cause': 820, 'contributing-cause': 820,
    'root-cause-candidate': 820, 'focal-event': 1090, event: 1090, impact: 1360,
    'corrective-action': 1360,
  };
  const counts = new Map<number, number>();
  return Object.fromEntries(nodes.map((node) => {
    const x = columns[node.type] ?? 20;
    const index = counts.get(x) || 0;
    counts.set(x, index + 1);
    return [node.id, { x, y: 28 + index * 198 }];
  })) as Record<string, Position>;
}

export function CausalCanvas({
  board,
  trackId,
  versionNumber,
  decisions,
  onReviewed,
}: {
  board: CausalBoard;
  trackId: string;
  versionNumber: number;
  decisions: HumanDecision[];
  onReviewed: () => Promise<void>;
}) {
  const storageKey = `rca:canvas:${trackId}`;
  const [positions, setPositions] = useState<Record<string, Position>>(() => {
    const fallback = initialPositions(board.nodes);
    if (typeof window === 'undefined') return fallback;
    try { return { ...fallback, ...JSON.parse(window.localStorage.getItem(storageKey) || '{}') }; }
    catch { return fallback; }
  });
  const [zoom, setZoom] = useState(0.82);
  const [dragging, setDragging] = useState<{ id: string; clientX: number; clientY: number; origin: Position } | null>(null);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState('');
  const [error, setError] = useState('');
  const height = Math.max(520, ...Object.values(positions).map((position) => position.y + 190));

  useEffect(() => {
    window.localStorage.setItem(storageKey, JSON.stringify(positions));
  }, [positions, storageKey]);

  const nodeById = useMemo(() => new Map(board.nodes.map((node) => [node.id, node])), [board.nodes]);

  async function review(targetId: string, action: 'accept' | 'reject' | 'close-branch') {
    setSaving(`${targetId}:${action}`);
    setError('');
    try {
      const response = await fetch(`/api/tracks/${trackId}/review`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          targetType: action === 'close-branch' ? 'causal-branch' : 'causal-node',
          targetId,
          action,
          notes,
        }),
      });
      const payload = await response.json() as { error?: string };
      if (!response.ok) throw new Error(payload.error || 'Unable to save the review decision.');
      setNotes('');
      await onReviewed();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to save the review decision.');
    } finally {
      setSaving('');
    }
  }

  return (
    <div className="interactive-causal-wrap">
      <div className="canvas-toolbar">
        <div><strong>Investigation canvas · V{versionNumber}</strong><span>Drag nodes to organize the working theory. Layout is a local viewing preference; review decisions create a new immutable version.</span></div>
        <label>Decision note<input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Optional rationale" /></label>
        <div><button type="button" onClick={() => setZoom((value) => Math.max(.45, value - .1))}>−</button><span>{Math.round(zoom * 100)}%</span><button type="button" onClick={() => setZoom((value) => Math.min(1.4, value + .1))}>+</button><button type="button" onClick={() => setPositions(initialPositions(board.nodes))}>Reset</button></div>
      </div>
      {error && <p className="form-error">{error}</p>}
      <div className="causal-viewport">
        <div className="causal-stage" style={{ width: 1630, height, transform: `scale(${zoom})` }}>
          <svg className="causal-edge-layer" width="1630" height={height} aria-hidden="true">
            <defs><marker id="causal-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" /></marker></defs>
            {board.edges.map((edge) => {
              const from = positions[edge.from];
              const to = positions[edge.to];
              if (!from || !to) return null;
              return <g key={edge.id}><line x1={from.x + 215} y1={from.y + 74} x2={to.x} y2={to.y + 74} className={`edge-${edge.status}`} markerEnd="url(#causal-arrow)" /><title>{edge.type}: {edge.rationale}</title></g>;
            })}
          </svg>
          {board.nodes.map((node) => {
            const position = positions[node.id] || { x: 20, y: 20 };
            const latestDecision = [...decisions].reverse().find((decision) => decision.targetId === node.id);
            return <article
              key={node.id}
              className={`canvas-node node-${node.type} ${node.verified ? 'verified' : ''}`}
              style={{ left: position.x, top: position.y }}
              onPointerDown={(event) => {
                if ((event.target as HTMLElement).closest('button')) return;
                event.currentTarget.setPointerCapture(event.pointerId);
                setDragging({ id: node.id, clientX: event.clientX, clientY: event.clientY, origin: position });
              }}
              onPointerMove={(event) => {
                if (!dragging || dragging.id !== node.id) return;
                setPositions((current) => ({
                  ...current,
                  [node.id]: {
                    x: Math.max(0, dragging.origin.x + (event.clientX - dragging.clientX) / zoom),
                    y: Math.max(0, dragging.origin.y + (event.clientY - dragging.clientY) / zoom),
                  },
                }));
              }}
              onPointerUp={() => setDragging(null)}
            >
              <div><span>{node.type.replaceAll('-', ' ')}</span><b>{node.status}</b></div>
              <h3>{node.label}</h3><p>{node.detail}</p>
              {latestDecision && <small className="human-decision-stamp">Human: {latestDecision.action}</small>}
              {REVIEWABLE.has(node.type) && <div className="node-review-actions">
                <button type="button" disabled={Boolean(saving)} onClick={() => review(node.id, 'accept')}>{saving === `${node.id}:accept` ? 'Saving…' : 'Accept'}</button>
                <button type="button" disabled={Boolean(saving)} onClick={() => review(node.id, 'reject')}>Reject</button>
                <button type="button" disabled={Boolean(saving)} onClick={() => review(node.id, 'close-branch')}>Close branch</button>
              </div>}
            </article>;
          })}
        </div>
      </div>
      <div className="canvas-legend">
        <span><i className="legend-supported" />Supported / verified</span>
        <span><i className="legend-proposed" />Proposed</span>
        <span><i className="legend-rejected" />Rejected</span>
        <span>{nodeById.size} nodes · {board.edges.length} links</span>
      </div>
    </div>
  );
}
