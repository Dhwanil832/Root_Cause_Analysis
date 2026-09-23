import Link from 'next/link';
import comparison from '@/src/history/featured-comparison.json';

export function FeaturedComparisonCard() {
  const meta = comparison as typeof comparison & { versions: { status?: string }[] };
  const controlled = String(comparison.kind) === 'controlled-revision';
  const pending = controlled && meta.versions.some(v => !['completed', 'partial'].includes(v.status || ''));
  return (
    <Link className="history-card" href={comparison.href} data-testid="featured-board-comparison" style={{ border: '2px solid #738743' }}>
      <div>
        <span>Pinned · {comparison.app} · {String(comparison.kind) === 'diagnostic-snapshots' ? 'Diagnostic snapshots — not published versions' : pending ? 'V1 frozen · V2 in progress' : controlled ? 'Partial V1 + controlled V2' : 'Saved V1 + V2'}</span>
        <h2>{comparison.title}</h2>
        <p>{comparison.description}</p>
      </div>
      <div className="history-models">
        <span><strong>{comparison.modelName}</strong> · {pending ? 'Open live investigation' : 'Compare causal boards'}</span>
        <span>{comparison.versions.map(v => `V${v.number}: ${v.nodes} nodes / ${v.edges} links`).join(' → ')}</span>
      </div>
      <b aria-hidden="true">→</b>
    </Link>
  );
}
