"""Run one connected case with current or verified historical core."""
import argparse, hashlib, json, os, sys, signal, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
active_file = ROOT/'active-harness.json'
default_arm = json.loads(active_file.read_text())['arm'] if active_file.exists() else 'runtime'
ap.add_argument('arm', nargs='?', default=default_arm, choices=['runtime'])
args = ap.parse_args()
ARM = ROOT/args.arm
sys.path.insert(0, str(ARM/'prototype'))
from rca import engine, provider
from rca.storage import read, save, now, digest
import codex_adapter

PACKAGE = ROOT/'benchmark/R3-investigation-v1'
CASE = ROOT/'runs/gpt/case'

def status(phase, **rest):
    data=dict(at=now(), arm=args.arm, pid=os.getpid(), phase=phase, **rest)
    save(ROOT/'runs/gpt/status.json',data)
    print(json.dumps(data),flush=True)

def client(prompt,packet,folder):
    status('generating', role=packet['assignment']['kind'], call=str(folder),
           model='gpt-5.5', completed_calls=len(read(CASE/'state.json')['calls']))
    return codex_adapter.call(prompt,packet,folder)

def stop(signum, frame): raise KeyboardInterrupt

def main():
    signal.signal(signal.SIGTERM,stop)
    lock=read(ARM/'runtime-lock.json')
    assert all(hashlib.sha256((ARM/f).read_bytes()).hexdigest()==h for f,h in lock['files'].items()), 'Snapshot changed'
    freeze=read(PACKAGE/'FREEZE.json')
    assert all(hashlib.sha256((PACKAGE/f).read_bytes()).hexdigest()==h for f,h in freeze['files'].items()), 'Benchmark changed'
    if not (CASE/'state.json').exists():
        start=read(PACKAGE/'public/start.json')
        s=engine.create(CASE,start['description'],[PACKAGE/'public/records'/(i+'.json') for i in start['initial_source_ids']],'gpt')
        s['execution_profile']=dict(codex_adapter.PROFILE)
        s['execution_profile_hash']=digest(s['execution_profile'])
        save(CASE/'state.json',s)
    else:
        s=read(CASE/'state.json')
        if s['phase']!='ready':raise RuntimeError('Existing case is not ready; no implicit retry of rejected/failed output.')
    failure=None
    try:
        s=engine.run(CASE,max_calls=None,client=client)
    except Exception as exc:
        failure=dict(category=getattr(exc,'category','runtime_error'),detail=str(exc),type=type(exc).__name__)
        print(traceback.format_exc(),flush=True)
        s=read(CASE/'state.json')
    requests=[dict(id=k,version=v['version'],record=v['record'],coverage=v.get('coverage',[]))
        for k,v in s['ledger'].items() if v['record']['kind']=='request'
        and v['record']['status'] in ['awaiting_user','partial'] and not v.get('superseded_by')]
    result=dict(arm=args.arm, model='gpt-5.5', transport='codex_chatgpt',phase=s['phase'],
        calls=len(s['calls']),records=len(s['ledger']),feedback=s.get('feedback'),failure=failure,
        requests_for_custodian=requests, sources=list(s['sources']),score=None,at=now())
    save(ROOT/'runs/gpt/execution-summary.json',result)
    status('paused_or_terminal',result=result)

if __name__=='__main__':
    try: main()
    except KeyboardInterrupt:
        status('interrupted');sys.exit(130)
    except Exception as exc:
        status('launcher_error',detail=str(exc));raise
