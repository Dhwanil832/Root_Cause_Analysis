"""Run a single matched ablation profile; no automatic multiple paid trials."""
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from main import main
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('profile',choices=['v1_basic','v2_full','v2_prompts_only','v2_methods_only','ablation_no_llm','ablation_v2_frontier_only','ablation_v2_planner_only','ablation_v2_route_only','ablation_v2_assessor_only','ablation_v2_planner_and_routes','ablation_v2_iris_specialist']);p.add_argument('--mode',choices=['fixture','live'],default='fixture');p.add_argument('--max-actions',default='18');a=p.parse_args()
    raise SystemExit(main(['--mode',a.mode,'--config','config/experiments/'+a.profile+'.yaml',
          '--max-actions',a.max_actions,'--output','outputs/experiment_'+a.profile]))
