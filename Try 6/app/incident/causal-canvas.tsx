'use client';

import { useEffect, useId, useMemo, useRef, useState } from 'react';
import type { CausalBoard, CausalNode, HumanDecision } from '@/src/domain/types';
import { RejectedConnections } from './rejected-connections';

type Position = { x: number; y: number };

const REVIEWABLE = new Set(['condition', 'change', 'barrier', 'direct-cause', 'contributing-cause', 'root-cause-candidate']);

function initialPositions(nodes: CausalNode[], compact = false) {
  const columns: Record<string, number> = {
    evidence: 20, unknown: 20, condition: 280, change: 280, barrier: 550,
    'human-decision-action': 550, 'direct-cause': 820, 'contributing-cause': 820,
    'root-cause-candidate': 820, 'focal-event': 1090, event: 1090, impact: 1360,
    'corrective-action': 1360,
  };
  const counts = new Map<number, number>();
  const usedColumns = [...new Set(nodes.map(node => columns[node.type] ?? 20))].sort((a, b) => a - b);
  return Object.fromEntries(nodes.map((node) => {
    const originalColumn = columns[node.type] ?? 20;
    const x = compact ? 20 + usedColumns.indexOf(originalColumn) * 270 : originalColumn;
    const index = counts.get(x) || 0;
    counts.set(x, index + 1);
    return [node.id, { x, y: 28 + index * (compact ? 380 : 280) }];
  })) as Record<string, Position>;
}

export function CausalCanvas({
  board,
  trackId,
  versionNumber,
  decisions,
  onReviewed,
  provisional = false,
  readOnly = false,
  viewLabel,
}: {
  board: CausalBoard;
  trackId: string;
  versionNumber: number;
  decisions: HumanDecision[];
  onReviewed: () => Promise<void>;
  provisional?: boolean;
  readOnly?: boolean;
  viewLabel?: string;
}) {
  const storageKey = `rca:canvas:${trackId}${readOnly ? ':archive-layout-v1' : ''}`;
  const arrowId = `causal-arrow-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const [positions, setPositions] = useState<Record<string, Position>>(() => {
    const fallback = initialPositions(board.nodes, readOnly);
    if (typeof window === 'undefined') return fallback;
    try { return { ...fallback, ...JSON.parse(window.localStorage.getItem(storageKey) || '{}') }; }
    catch { return fallback; }
  });
  const [zoom, setZoom] = useState(0.82);
  const [dragging, setDragging] = useState<{ id: string; clientX: number; clientY: number; origin: Position } | null>(null);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState('');
  const [error, setError] = useState('');
  const height = Math.max(520, ...Object.values(positions).map((position) => position.y + (readOnly ? 380 : 280)));
  const width = readOnly ? Math.max(300, ...Object.values(positions).map(position => position.x + 255)) : 1630;
  const viewportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!readOnly || !viewportRef.current) return;
    const viewport = viewportRef.current;
    const observer = new ResizeObserver(() => setZoom(Math.max(.2, Math.min(1, (viewport.clientWidth - 24) / width))));
    observer.observe(viewport);
    return () => observer.disconnect();
  }, [readOnly, width]);

  useEffect(() => {
    window.localStorage.setItem(storageKey, JSON.stringify(positions));
  }, [positions, storageKey]);

  const nodeById = useMemo(() => new Map(board.nodes.map((node) => [node.id, node])), [board.nodes]);
  const findingsFor = (id: string) => board.verificationFindings.filter(f => f.targetId === id);
  const blocked = (id: string) => findingsFor(id).some(f => f.severity === 'blocking');

  async function review(targetId: string, action: 'accept' | 'reject' | 'close-branch') {
    if (provisional || readOnly) return;
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
          expectedVersion:versionNumber,
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
        <div><strong>Investigation canvas · {viewLabel || `${provisional ? 'Pending V' : 'V'}${versionNumber}`}</strong><span>{readOnly ? 'Preserved board — read-only. Dragging and zoom affect this view only; review actions are disabled.' : provisional ? 'Saved checkpoint only — not a committed version or an approved RCA. Investigation and verification may be incomplete; review actions are disabled.' : 'Drag nodes to organize the working theory. Layout is a local viewing preference; review decisions create a new immutable version.'}</span></div>
        {!provisional && !readOnly && <label>Decision note<input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Optional rationale" /></label>}
        <div><button type="button" onClick={() => setZoom((value) => Math.max(readOnly ? .2 : .45, value - .1))}>−</button><span>{Math.round(zoom * 100)}%</span><button type="button" onClick={() => setZoom((value) => Math.min(1.4, value + .1))}>+</button>{readOnly && <button type="button" onClick={() => setZoom(Math.max(.2, Math.min(1, ((viewportRef.current?.clientWidth || width) - 24) / width)))}>Fit</button>}<button type="button" onClick={() => setPositions(initialPositions(board.nodes, readOnly))}>Reset</button></div>
      </div>
      {error && <p className="form-error">{error}</p>}
      <div className="causal-viewport" ref={viewportRef}>
        <div className="causal-stage" style={{ width, height, transform: `scale(${zoom})` }}>
          <svg className="causal-edge-layer" width={width} height={height} aria-hidden="true">
            <defs><marker id={arrowId} markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#77837c" /></marker></defs>
            {board.edges.map((edge) => {
              const from = positions[edge.from];
              const to = positions[edge.to];
              if (!from || !to) return null;
              const unresolved = blocked(edge.id) || blocked(edge.from) || blocked(edge.to) || !edge.verified;
              return <g key={edge.id}><line x1={from.x + 215} y1={from.y + 74} x2={to.x} y2={to.y + 74} className={`edge-${unresolved ? 'unknown' : edge.status}`} markerEnd={`url(#${arrowId})`} /><title>{unresolved ? 'UNRESOLVED' : 'EVIDENCE-REVIEWED'} · {edge.type}: {edge.rationale} {findingsFor(edge.id).map(f => f.issue).join(' ')}</title></g>;
            })}
          </svg>
          {board.nodes.map((node) => {
            const position = positions[node.id] || { x: 20, y: 20 };
            const latestDecision = [...decisions].reverse().find((decision) => decision.targetId === node.id);
            return <article
              key={node.id}
              className={`canvas-node node-${node.type} ${blocked(node.id) ? 'disputed' : node.verified ? 'verified' : ''}`}
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
              <div><span>{node.type.replaceAll('-', ' ')}</span><b>{node.status === 'rejected' ? 'Rejected' : blocked(node.id) ? 'Unresolved' : node.verified ? 'Evidence-reviewed' : 'Not verified'}</b></div>
              <h3>{node.label}</h3><p>{node.detail}</p>
              <small>Agent proposal: {node.proposedStatus || node.status}</small>
              {findingsFor(node.id).length > 0 && <details className="node-findings" onPointerDown={e => e.stopPropagation()}><summary>{findingsFor(node.id).length} review finding(s)</summary>{findingsFor(node.id).map(f => <div key={f.id}>{f.issue}<br /><strong>Needed:</strong> {f.evidenceNeeded}</div>)}</details>}
              {node.humanStatus && node.humanStatus!=='unreviewed' ? <small className="human-decision-stamp">Human review: {node.humanStatus}{node.humanStatus==='reopened'?' — new evidence requires review':''}</small>
                : latestDecision && <small className="human-decision-stamp">Human: {latestDecision.action}</small>}
              {!provisional && !readOnly && REVIEWABLE.has(node.type) && <div className="node-review-actions">
                <button type="button" disabled={Boolean(saving)} onClick={() => review(node.id, 'accept')}>{saving === `${node.id}:accept` ? 'Saving…' : 'Accept'}</button>
                <button type="button" disabled={Boolean(saving)} onClick={() => review(node.id, 'reject')}>Reject</button>
                <button type="button" disabled={Boolean(saving)} onClick={() => review(node.id, 'close-branch')}>Close branch</button>
              </div>}
            </article>;
          })}
        </div>
      </div>
      <div className="canvas-legend">
        <span><i className="legend-supported" />Model evidence-reviewed — not human acceptance</span>
        <span><i className="legend-proposed" />Proposed</span>
        <span><i className="legend-rejected" />Rejected</span>
        <span>{nodeById.size} nodes · {board.edges.length} links · {board.rejectedEdges?.length || 0} rejected proposals</span>
      </div>
      <details className="edge-review-list"><summary>Connection evidence and unresolved findings ({board.edges.length})</summary>{board.edges.map(edge => <article key={edge.id}>
        <strong>{nodeById.get(edge.from)?.label} → {nodeById.get(edge.to)?.label}</strong>
        <p>{edge.status === 'rejected' ? 'Rejected' : edge.verified && !blocked(edge.id) && !blocked(edge.from) && !blocked(edge.to) ? 'Evidence-reviewed' : 'Not verified'} · {edge.rationale}</p>
        {findingsFor(edge.id).map(f => <p key={f.id}>{f.issue} Needed: {f.evidenceNeeded}</p>)}
      </article>)}</details>
      <RejectedConnections edges={board.rejectedEdges} />
    </div>
  );
}
