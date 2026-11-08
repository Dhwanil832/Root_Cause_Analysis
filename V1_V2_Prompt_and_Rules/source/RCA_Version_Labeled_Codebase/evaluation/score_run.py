"""Evaluate a saved run; source content/reference never re-enters model context."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from evaluation.metrics.behavioral import inspect_run
from evaluation.metrics.reviewer_sheet import write_sheet
from shared.config_loader import ROOT


def score(root,fixture_reference=False):
    root=Path(root)
    ref=(ROOT/'evaluation/private_reference/wet_floor_structural_checks.json') if fixture_reference else None
    result=inspect_run(root,ref)
    (root/'evaluation_report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    result['human_review_rows']=write_sheet(root,root/'manual_review.csv')
    # Save row count in the report, without asserting review was done.
    (root/'evaluation_report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('run_dir',type=Path)
    ap.add_argument('--fixture-reference',action='store_true',help='Use builder-only expected states for synthetic wet-floor fixture')
    a=ap.parse_args()
    print(json.dumps(score(a.run_dir,a.fixture_reference),indent=2))

if __name__=='__main__':main()
