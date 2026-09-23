import Link from 'next/link';
import comparison from '@/src/history/featured-comparison.json';

export function FeaturedComparisonCard() {
  return (
    <Link className="history-card" href={comparison.href} data-testid="featured-board-comparison" style={{ border: '2px solid #738743' }}>
      <div>
        <span>Pinned · {comparison.app} · {comparison.kind === 'diagnostic-snapshots' ? 'Diagnostic snapshots — not published versions' : 'Saved V1 + V2'}</span>
        <h2>{comparison.title}</h2>
        <p>{comparison.description}</p>
      </div>
      <div className="history-models">
        <span><strong>{comparison.modelName}</strong> · Compare causal boards</span>
        <span>{comparison.versions.map(v => `V${v.number}: ${v.nodes} nodes / ${v.edges} links`).join(' → ')}</span>
      </div>
      <b aria-hidden="true">→</b>
    </Link>
  );
}

