"""Portable Ollama transport. Core RCA prompts/controller are unchanged.

Streaming preserves partial output and reports counts without printing thinking text.
"""
import copy, json, time, urllib.request, urllib.error
from pathlib import Path
from common import provider, schema, read, save, digest, now

def api(endpoint,route,payload=None,timeout=30):
    return json.loads(provider.exchange(endpoint.rsplit('/',1)[0]+'/'+route,payload,timeout=timeout)[0])

def pull(endpoint,name):
    url=endpoint.rsplit('/',1)[0]+'/pull'
    req=urllib.request.Request(url,data=json.dumps(dict(model=name,stream=True)).encode(),headers={'Content-Type':'application/json'})
    last_print=0
    with urllib.request.urlopen(req,timeout=None) as res:
        for line in res:
            obj=json.loads(line)
            if obj.get('error'):raise RuntimeError(obj['error'])
            if time.monotonic()-last_print>15 or obj.get('status')=='success':
                print(json.dumps(dict(model=name,download=obj)),flush=True);last_print=time.monotonic()

def resolve(entry,settings,endpoint):
    name=entry['name'];models=api(endpoint,'tags')['models']
    actual=next((m for m in models if m['name']==name or m.get('model')==name),None)
    if actual is None:
        pull(endpoint,name);actual=next((m for m in api(endpoint,'tags')['models'] if m['name']==name or m.get('model')==name),None)
    if actual is None:raise RuntimeError('Pulled tag not found; specify an explicit tag, e.g. model:latest')
    if entry.get('expected_digest') and entry['expected_digest']!=actual['digest']:
        raise provider.CallFailure('model_mismatch',f'{name}: registry digest changed. Historical pin {entry["expected_digest"]}; installed {actual["digest"]}. Use a separate unpinned entry/run deliberately, not silent substitution.')
    info=api(endpoint,'show',dict(model=name))
    native={k:v for k,v in info.get('model_info',{}).items() if k.endswith('.context_length') and 'vision' not in k}
    if not native and actual.get('details',{}).get('context_length'):
        native={'details.context_length':actual['details']['context_length']}
    lengths=set(native.values())
    if len(lengths)!=1:raise provider.CallFailure('context_configuration','Cannot uniquely identify native context: '+str(native))
    n=entry.get('num_ctx') or next(iter(lengths))
    if n>next(iter(lengths)):raise provider.CallFailure('context_configuration','Configured context exceeds native model context')
    capabilities=info.get('capabilities',actual.get('capabilities',[]))
    if entry.get('think',False) and 'thinking' not in capabilities:
        raise provider.CallFailure('adapter_incompatibility','Thinking requested but not advertised by this model')
    options=copy.deepcopy(settings['options']);options['num_ctx']=n
    version=api(endpoint,'version')['version']
    if version!=settings['ollama_version']:raise provider.CallFailure('adapter_version_mismatch','Server version mismatch')
    cfg=dict(provider='ollama_linux',model=name,digest=actual['digest'],server_version=version,
             think=entry.get('think',False),thinking_supported='thinking' in capabilities,
             truncate=False,shift=False,timeout_seconds=None,options=options,require_full_gpu=settings['require_full_gpu'])
    return cfg,dict(server_version=version,model=actual,native_contexts=native,show=info)

def loaded(endpoint,config):
    result=api(endpoint,'ps')
    m=next((m for m in result['models'] if m.get('digest')==config['digest']),None)
    if not m or m.get('context_length')!=config['options']['num_ctx']:
        raise provider.CallFailure('context_configuration','Loaded context does not match the recorded configuration')
    if config['require_full_gpu'] and (not m.get('size') or m.get('size_vram',0)<m['size']):
        raise provider.CallFailure('hardware_capacity','Model/context is not fully GPU-resident. No silent CPU fallback or context reduction. '+json.dumps(m))
    return result

def preload(endpoint,config):
    api(endpoint,'chat',dict(model=config['model'],messages=[],stream=False,keep_alive=-1,options=config['options']),timeout=None)
    return loaded(endpoint,config)

def unload(endpoint,name):
    api(endpoint,'generate',dict(model=name,keep_alive=0),timeout=30)

def request_for(prompt,packet,config):
    req=dict(model=config['model'],messages=provider.messages(prompt,packet),format=schema.OUTPUT,
             stream=True,truncate=False,shift=False,keep_alive=-1,options=copy.deepcopy(config['options']))
    if config['thinking_supported']:req['think']=config['think']
    return req

def aggregate_event(event,text,thinking):
    if event.get('error'):raise provider.CallFailure('provider_protocol',event['error'])
    message=event.get('message',{})
    text.append(message.get('content',''));thinking.append(message.get('thinking',''))
    if event.get('done'):
        final=copy.deepcopy(event);final['message']=dict(role='assistant',content=''.join(text),thinking=''.join(thinking))
        return final
    return None

def call(prompt,packet,folder,config,endpoint):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    req=request_for(prompt,packet,config)
    save(folder/'request.json',req);save(folder/'packet.json',packet)
    save(folder/'started.json',dict(at=now(),execution_profile=config,transport_endpoint=endpoint,request_hash=digest(req),schema_hash=digest(schema.OUTPUT)))
    start=time.monotonic();text=[];thinking=[]
    try:
        identity=api(endpoint,'tags');entry=next((m for m in identity['models'] if m['name']==config['model']),{})
        if entry.get('digest')!=config['digest']:raise provider.CallFailure('model_mismatch','Model changed during run')
        if api(endpoint,'version')['version']!=config['server_version']:raise provider.CallFailure('adapter_version_mismatch','Server changed during run')
        save(folder/'identity.json',entry)
        request=urllib.request.Request(endpoint,data=json.dumps(req).encode(),headers={'Content-Type':'application/json'})
        final=None;last_print=0
        with urllib.request.urlopen(request,timeout=None) as response,(folder/'response.jsonl').open('wb') as log:
            for raw in response:
                log.write(raw);log.flush()
                event=json.loads(raw);final=aggregate_event(event,text,thinking)
                if time.monotonic()-last_print>30:
                    progress=dict(at=now(),seconds=round(time.monotonic()-start),answer_characters=sum(map(len,text)),thinking_characters=sum(map(len,thinking)))
                    save(folder/'progress.json',progress)
                    print(json.dumps(dict(model=config['model'],call=str(folder),**progress)),flush=True);last_print=time.monotonic()
                if final is not None:break
        (folder/'answer.txt').write_text(''.join(text))
        if final is None:raise provider.CallFailure('incomplete_response','Stream ended without a terminal response; partial chunks preserved')
        save(folder/'response.json',final)
        save(folder/'loaded-models.json',loaded(endpoint,config))
        data,answer,usage=provider.extract(final,config)
        save(folder/'result.json',dict(status='completed',seconds=round(time.monotonic()-start,3),usage=usage,model=config['model'],provider=config['provider'],answer_hash=digest(answer),request_hash=digest(req)))
        return data
    except Exception as exc:
        (folder/'answer.txt').write_text(''.join(text))
        detail=provider.diagnostic(exc,config)
        if isinstance(exc,urllib.error.HTTPError):
            body=exc.read().decode(errors='replace');(folder/'http_error.txt').write_text(provider.sanitize(body))
            low=body.lower()
            if any(s in low for s in ['context length','context window','exceeds the context','context size']):detail['category']='context_capacity'
            elif any(s in low for s in ['out of memory','allocation failed']):detail['category']='hardware_capacity'
        detail['seconds']=round(time.monotonic()-start,3);save(folder/'error.json',detail)
        raise provider.CallFailure(detail['category'],detail['detail']) from None
