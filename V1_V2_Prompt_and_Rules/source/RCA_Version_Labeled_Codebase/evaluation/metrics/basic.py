"""Descriptive completed-run metrics only; not accuracy, safety, or causal correctness."""
from __future__ import annotations
import json
from pathlib import Path

def read_metrics(run_dir):
    root=Path(run_dir)
    summary=json.loads((root/'summary.json').read_text())
    trace=json.loads((root/'trace.json').read_text())
    return dict(case=summary['case'],mode=summary.get('mode'),stop=summary['stop_reason'],
      provider_http_calls=summary['provider_http_calls'],steps=len(trace),
      documents=len(summary['sources_assessed']),corrections=len(summary['corrections']),
      causal_links=len(summary['causal_view']['links']),
      unresolved_gaps=sum(x['status']=='open' for x in summary['gaps']))
