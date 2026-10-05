"""Aggregate an already annotated run using the frozen 96-check rubric."""
import argparse
import json
from pathlib import Path
from review.frozen_score import score

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('folder', type=Path, help='Run with annotations.json and stage-windows.json')
args = parser.parse_args()
print(json.dumps(score(args.folder), indent=2))
