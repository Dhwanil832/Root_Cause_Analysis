"""Print descriptive run metrics without calling any language model."""
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluation.metrics.basic import read_metrics
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: python scripts/summarize_run.py outputs/demo')
    print(json.dumps(read_metrics(sys.argv[1]),indent=2))
