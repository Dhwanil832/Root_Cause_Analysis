"""One connected attempt; resumes only after reviewed evidence makes case ready."""
import argparse, os, traceback
from common import *
import adapter

ap=argparse.ArgumentParser()
ap.add_argument('model', choices=['qwen','gptoss','granite','hermes','mistral'])
args=ap.parse_args()
FOLDER=ROOT/'runs'/args.model
CASE=FOLDER/'case'
ENDPOINT='http://127.0.0.1:11434/api/chat'
config=read(ROOT/'profiles.json')[args.model]

def status(phase, **details):
    data=dict(at=now(),pid=os.getpid(),model=config['model'],phase=phase,**details)
    save(FOLDER/'status.json',data)
    print(__import__('json').dumps(data),flush=True)

def client(prompt,packet,folder):
    status('generating',role=packet['assignment']['kind'],call=str(folder))
    return adapter.call(prompt,packet,folder,config,ENDPOINT)

def main():
    verify()
    FOLDER.mkdir(parents=True,exist_ok=True)
    with engine.lock(FOLDER):
        if engine.statepath(CASE).exists():
            s=read(engine.statepath(CASE))
            assert s['phase']=='ready' and not s.get('pending_call'), 'No implicit retry of rejected/failed output'
            assert s['execution_profile']==config, 'Configuration changed'
        status('verifying_and_loading')
        settings=read(ROOT/'settings.json')
        settings['require_full_gpu']=config['require_full_gpu']
        resolved,identity=adapter.resolve(dict(name=config['model'],think=config['think'],expected_digest=config['digest']),settings,ENDPOINT)
        resolved['provider']=config['provider']
        assert resolved==config, 'Installed model settings changed'
        save(FOLDER/'identity.json',identity)
        save(FOLDER/'profile.json',config)
        failure=None
        try:
            save(FOLDER/'loaded-models.json',adapter.preload(ENDPOINT,config))
            if not engine.statepath(CASE).exists():
                start=read(PACKAGE/'public/start.json')
                s=engine.create(CASE,start['description'],[PACKAGE/'public/records'/(i+'.json') for i in start['initial_source_ids']],'qwen')
                s['execution_profile']=config
                s['execution_profile_hash']=digest(config)
                save(engine.statepath(CASE),s)
            s=engine.run(CASE,max_calls=None,client=client)
        except Exception as exc:
            failure=provider.diagnostic(exc,config)
            print(traceback.format_exc(),flush=True)
        finally:
            try: adapter.unload(ENDPOINT,config['model'])
            except Exception as exc: status('unload_warning',detail=str(exc))
        s=read(engine.statepath(CASE)) if engine.statepath(CASE).exists() else {}
        requests=[dict(id=k,version=v['version'],record=v['record'],coverage=v.get('coverage',[])) for k,v in s.get('ledger',{}).items() if v['record']['kind']=='request' and v['record']['status'] in ['awaiting_user','partial'] and not v.get('superseded_by')]
        result=dict(at=now(),model=config['model'],phase=s.get('phase','setup_error'),calls=len(s.get('calls',[])),records=len(s.get('ledger',{})),failure=failure,feedback=s.get('feedback'),requests_for_custodian=requests,sources=list(s.get('sources',{})),score=None)
        save(FOLDER/'execution-summary.json',result)
        status('paused_or_terminal',result=result)

if __name__=='__main__': main()
