"""Rebuild local HTML viewer from an existing saved trace, with no new model calls."""
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integrations.viewer import build_viewer
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('run',type=Path);args=a.parse_args()
    print(build_viewer(args.run/'trace.json',args.run/'summary.json',args.run/'investigation_viewer.html'))
