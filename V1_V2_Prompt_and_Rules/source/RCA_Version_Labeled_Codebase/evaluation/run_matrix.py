"""Reproducible V1/V2 prompt-vs-method ablations with isolated case states.

Live mode is an OPT-IN provider HTTP experiment. It NEVER uses authored model
responses if preflight or inference fails. Input documents are isolated from
private_reference; the offline evaluator alone loads developer expectations.
"""
from __future__ import annotations
import argparse,json,traceback
from pathlib import Path
from collections import OrderedDict
from shared.config_loader import load_config,ROOT
from shared.llm.client import ModelFailure
from orchestration.orchestrator import Investigator
from integrations.evidence_sources.synthetic_world import EvidenceWorld
from integrations.evidence_sources.local_folder import LocalEvidenceWorld
from evaluation.score_run import score

PROFILES=OrderedDict([
    ('v1_prompt_only','config/experiments/v1_basic.yaml'),
    ('v2_prompts_only','config/experiments/v2_prompts_only.yaml'),
    ('v2_methods_only','config/experiments/v2_methods_only.yaml'),
    ('v2_full','config/experiments/v2_full.yaml'),
])


def run_matrix(output, mode='fixture', profiles=None, max_actions=18, model=None,
               provider=None, incident=None, evidence_dir=None, case_id=None,
               base_url=None):
    if mode not in ('fixture','live'):
        raise ValueError('mode must be fixture or live')
    if bool(incident)!=bool(evidence_dir):
        raise ValueError('incident and evidence_dir must be supplied together')
    destination=Path(output);destination.mkdir(parents=True,exist_ok=True)
    selected=profiles or list(PROFILES)
    results=[]
    for name in selected:
        if name not in PROFILES:raise ValueError(f'Unknown profile: {name}')
        run_dir=destination/name
        run_dir.mkdir(parents=True,exist_ok=True)
        config=load_config(PROFILES[name])
        if model:config['llm']['model']=model
        if provider:config['llm']['provider']=provider
        if base_url:config['llm']['base_url']=base_url
        if case_id:config['project']['case_id']=case_id
        world=(LocalEvidenceWorld(incident,evidence_dir) if incident else
               EvidenceWorld(ROOT/'evaluation/fixtures/wet_floor/documents.json'))
        runner=None
        try:
            runner=Investigator(world,config,mode=mode,max_steps=max_actions,
                  case_id=config['project']['case_id'],
                  fixture_responses=ROOT/'evaluation/private_reference/fixture_responses_DESIGNER_ONLY.json'
                  if mode=='fixture' else None)
            runner.run()
            runner.output(run_dir)
            report=score(run_dir,fixture_reference=(mode=='fixture' and not incident))
            results.append({'profile':name,'run_status':'completed',
                            'provider_http_completions':report['provider_http_completions'],
                            'report':str((run_dir/'evaluation_report.json').relative_to(destination)),
                            'authored_fixture_invariants':report.get('authored_fixture_invariants',{}).get('checks')})
        except Exception as exc:
            # Preserve EVERY completed HTTP response and partial revision state.
            # No authored fallback, invented result, or fake model completion.
            (run_dir/'EXECUTION_FAILED.txt').write_text(traceback.format_exc())
            count=0;partial=None
            if runner is not None:
                runner.stop_reason='execution_error'
                runner.blockers.append({'type':type(exc).__name__,'message':str(exc)})
                runner.record('execution_error',reason=f'{type(exc).__name__}: {exc}')
                runner.output(run_dir)
                partial=score(run_dir,fixture_reference=False)
                count=partial['provider_http_completions']
            results.append({'profile':name,'run_status':'failed_or_partial',
                            'error_type':type(exc).__name__,'error_message':str(exc),
                            'provider_http_completions':count,
                            'report':str((run_dir/'evaluation_report.json').relative_to(destination)) if partial else None})
    out={'mode':mode,'profiles':results,'independent_model_validation':False,
         'note':('AUTHORED test-double run; not model intelligence or causal correctness'
                 if mode=='fixture' else
                 'Live HTTP responses are model executions but causal accuracy still requires blinded expert review'),
         'fairness':'All runs receive fresh evidence worlds; algorithms and prompts varied separately; actual costs must be compared.',
         'source_environment':'separate local case' if incident else 'single wet-floor synthetic fixture',
    }
    (destination/'MATRIX_REPORT.json').write_text(json.dumps(out,indent=2))
    return out


def main(argv=None):
    ap=argparse.ArgumentParser(description='Compare V1 prompt-only and V2 prompt/method ablations')
    ap.add_argument('--mode',choices=('fixture','live'),required=True)
    ap.add_argument('--output',type=Path,default=ROOT/'outputs/matrix')
    ap.add_argument('--profiles',nargs='+',choices=list(PROFILES),default=None)
    ap.add_argument('--max-actions',type=int,default=18)
    ap.add_argument('--model',default=None)
    ap.add_argument('--provider',default=None)
    ap.add_argument('--base-url',default=None,
                    help='Provider host/base URL; native Ollama expects the server origin, e.g. http://localhost:11434')
    ap.add_argument('--case-id',default=None)
    ap.add_argument('--incident',type=Path,default=None)
    ap.add_argument('--evidence-dir',type=Path,default=None)
    a=ap.parse_args(argv)
    print(json.dumps(run_matrix(a.output,a.mode,a.profiles,a.max_actions,a.model,a.provider,
                                a.incident,a.evidence_dir,a.case_id,a.base_url),indent=2))

if __name__=='__main__':main()
