#!/usr/bin/env python3
"""One-command local validation of V2 code and authored ablation fixtures."""
from __future__ import annotations
import subprocess,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    print('Running 95 inherited kernel tests + new RCA agent/method tests...',flush=True)
    subprocess.run([sys.executable,'-m','pytest','-q'],cwd=ROOT,check=True)
    print('Running four authored-fixture V1/V2 ablations...',flush=True)
    subprocess.run([sys.executable,'-m','evaluation.run_matrix','--mode','fixture',
                    '--output','outputs/v2_factorial'],cwd=ROOT,check=True)
    report=json.loads((ROOT/'outputs/v2_factorial/MATRIX_REPORT.json').read_text())
    assert len(report['profiles'])==4
    assert all(x['run_status']=='completed' and x['provider_http_completions']==0
               for x in report['profiles'])
    print('Offline checks passed. This does not establish independent model performance.')
    return 0

if __name__=='__main__':raise SystemExit(main())
