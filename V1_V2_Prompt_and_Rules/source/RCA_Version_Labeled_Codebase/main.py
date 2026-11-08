#!/usr/bin/env python3
"""CLI: `python main.py --mode fixture` or `python main.py --mode live`."""
from __future__ import annotations
import argparse,sys,json,traceback
from pathlib import Path
from shared.config_loader import load_config,ROOT
from shared.env_loader import load_env_file
from shared.llm.client import ModelFailure
from orchestration.orchestrator import Investigator
from integrations.evidence_sources.synthetic_world import EvidenceWorld
from integrations.evidence_sources.local_folder import LocalEvidenceWorld
from integrations.viewer import build_viewer

def main(argv=None):
    parser=argparse.ArgumentParser(description='Modular Progressive RCA: model-driven investigation with v2 provenance')
    parser.add_argument('--mode',choices=['fixture','live'],required=True,
        help='fixture is AUTHORED responses; live makes actual provider HTTP calls')
    parser.add_argument('--config',default=None,help='YAML override, e.g. config/experiments/ablation_no_llm.yaml')
    parser.add_argument('--model',default=None,help='Override all role model names')
    parser.add_argument('--provider',choices=['openrouter','openai','ollama','compatible'],default=None)
    parser.add_argument('--base-url',default=None)
    parser.add_argument('--max-actions',type=int,default=None)
    parser.add_argument('--case-id',default=None)
    parser.add_argument('--incident',type=Path,default=None,help='Initial .md/.txt incident for local-folder environment')
    parser.add_argument('--evidence-dir',type=Path,default=None,help='Folder of custodian subfolders for local evidence')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/latest')
    args=parser.parse_args(argv)
    if args.max_actions is not None and not (1<=args.max_actions<=100):parser.error('--max-actions must be 1..100')
    if bool(args.incident) != bool(args.evidence_dir):parser.error('--incident and --evidence-dir must be supplied together')
    load_env_file(ROOT/'.env')
    config=load_config(args.config)
    if args.model:config['llm']['model']=args.model
    if args.provider:config['llm']['provider']=args.provider
    if args.base_url:config['llm']['base_url']=args.base_url
    if args.incident:
        world=LocalEvidenceWorld(args.incident,args.evidence_dir)
    else:
        world=EvidenceWorld(ROOT/'evaluation/fixtures/wet_floor/documents.json')
    try:
        investigator=Investigator(world,config,args.mode,max_steps=args.max_actions,
                                  case_id=args.case_id,fixture_responses=ROOT/'evaluation/private_reference/fixture_responses_DESIGNER_ONLY.json')
    except (ModelFailure,ValueError,FileNotFoundError) as e:
        print(f'PREFLIGHT FAILED: {e}',file=sys.stderr)
        return 2
    try:
        investigator.run()
        status=0
    except Exception as exc:
        # Save the actual partial state; no deterministic response is substituted.
        investigator.stop_reason='execution_error'
        investigator.blockers.append({'type':type(exc).__name__,'message':str(exc)})
        investigator.record('execution_error',reason=f'{type(exc).__name__}: {exc}')
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/'RUN_FAILED.txt').write_text('Execution halted without fallback:\n'+traceback.format_exc())
        print('RUN FAILED:',type(exc).__name__,str(exc),file=sys.stderr)
        status=1
    summary=investigator.output(args.output)
    if investigator.events:
        build_viewer(args.output/'trace.json',args.output/'summary.json',args.output/'investigation_viewer.html')
    print(json.dumps({k:summary[k] for k in ('case','mode','stop_reason','calls_total','provider_http_calls','sources_assessed')},indent=2))
    print('Saved trace:',args.output/'trace.json')
    print('Viewer:',args.output/'investigation_viewer.html')
    return status

if __name__=='__main__':raise SystemExit(main())
