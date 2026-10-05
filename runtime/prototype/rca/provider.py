"""Two transports; identical messages/schema and explicit capacity failures."""
import copy,json,os,ssl,time,re,urllib.request,urllib.error
from pathlib import Path
from .storage import save,digest,now
from .schema import OUTPUT,validate
MODEL='gpt-5.5-2026-04-23'
QWEN_MODEL='qwen3.5:latest'
QWEN_DIGEST='6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7'
OLLAMA_VERSION='0.32.3'
PROFILES={
 'gpt':dict(provider='gpt',model=MODEL,reasoning_effort='medium',max_output_tokens=128000,timeout_seconds=None),
 'qwen':dict(provider='qwen',model=QWEN_MODEL,digest=QWEN_DIGEST,server_version=OLLAMA_VERSION,endpoint='http://127.0.0.1:11434/api/chat',think=False,truncate=False,shift=False,timeout_seconds=None,options=dict(temperature=0,seed=42,top_p=0.8,top_k=20,min_p=0,presence_penalty=0,repeat_penalty=1,num_ctx=262144,num_predict=-1))}

def profile(name):return copy.deepcopy(PROFILES[name])
def validate_profile(config):
 if config!=PROFILES.get(config.get('provider')):raise ValueError('Execution profile changed; use a separately qualified new case, never silently change a comparison arm.')

def credential():
 key=os.environ.get('OPENAI_API_KEY','').strip()
 p=Path(__file__).resolve().parents[2]/'.env.local'
 if not key and p.exists():
  for line in p.read_text().splitlines():
   if line.strip().startswith('OPENAI_API_KEY='):key=line.strip().split('=',1)[1].strip().strip('\"\'')
 if not key or key=='...' or any(c.isspace() for c in key):raise CallFailure('configuration','OPENAI_API_KEY is not configured correctly; set it in the documented server-side environment file.')
 return key
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
class CallFailure(RuntimeError):
 def __init__(self,category,detail,**metadata):super().__init__(detail);self.category=category;self.metadata=metadata

def messages(prompt,packet):
 return [dict(role='system',content=prompt),dict(role='user',content=json.dumps(packet,ensure_ascii=False))]

def make_request(prompt,packet,config=None):
 config=config or profile('gpt');validate_profile(config);msg=messages(prompt,packet)
 if config['provider']=='qwen':
  return dict(model=config['model'],messages=msg,format=OUTPUT,think=config['think'],stream=False,truncate=False,shift=False,options=copy.deepcopy(config['options']))
 return dict(model=config['model'],input=msg,reasoning={'effort':config['reasoning_effort']},max_output_tokens=config['max_output_tokens'],store=False,stream=False,truncation='disabled',text={'format':{'type':'json_schema','name':'rca_step','strict':True,'schema':OUTPUT}})

def exchange(url,payload=None,key=None,timeout=600):
 headers={'Content-Type':'application/json'}
 if key:headers['Authorization']='Bearer '+key
 req=urllib.request.Request(url,data=json.dumps(payload).encode() if payload is not None else None,headers=headers,method='POST' if payload is not None else 'GET')
 cafile='/etc/ssl/cert.pem' if Path('/etc/ssl/cert.pem').exists() else None
 opener=urllib.request.build_opener(NoRedirect,urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=cafile)))
 with opener.open(req,timeout=timeout) as response:return response.read(),response.headers.get('x-request-id')

def qwen_identity(config):
 base=config['endpoint'].rsplit('/',1)[0]
 version=json.loads(exchange(base+'/version',timeout=15)[0])
 tags=json.loads(exchange(base+'/tags',timeout=15)[0])
 model=next((m for m in tags['models'] if m['name']==config['model']),None)
 if version.get('version')!=config['server_version']:raise CallFailure('adapter_version_mismatch',f"Ollama version mismatch: expected {config['server_version']}, received {version.get('version')}.")
 if not model or model.get('digest')!=config['digest']:raise CallFailure('model_mismatch',f"Model {config['model']} digest mismatch: expected {config['digest']}, received {(model or {}).get('digest')}.")
 if model.get('details',{}).get('context_length')!=config['options']['num_ctx']:raise CallFailure('context_configuration',f"Model {config['model']} context mismatch: expected {config['options']['num_ctx']}, received {model.get('details',{}).get('context_length')}.")
 return dict(server=version,model=model)

def extract(res,config):
 """Validate transport completion BEFORE accepting even a valid JSON prefix."""
 if res.get('model')!=config['model']:raise CallFailure('model_mismatch',f"Response model mismatch: expected {config['model']}, received {res.get('model')}.")
 if config['provider']=='gpt':
  if res.get('status')!='completed':
   why=(res.get('incomplete_details') or {}).get('reason')
   raise CallFailure('output_limit' if why=='max_output_tokens' else 'incomplete_response','Response did not complete: '+str(why))
  contents=[c for x in res.get('output',[]) if x.get('type')=='message' for c in x.get('content',[])]
  if any(c.get('type')=='refusal' for c in contents):raise CallFailure('refusal','Model returned a refusal.')
  answer='\n'.join(c['text'] for c in contents if c.get('type')=='output_text');usage=res.get('usage',{})
 else:
  if not res.get('done') or res.get('done_reason')!='stop':
   # With num_predict=-1 a length stop is not an imposed output-token quota.
   # Preserve it as a backend/context limit; do not call it a reasoning error.
   category='backend_generation_limit' if res.get('done_reason')=='length' and config['options']['num_predict']==-1 else 'output_limit' if res.get('done_reason')=='length' else 'incomplete_response'
   raise CallFailure(category,f"{config['model']} did not stop normally: done={res.get('done')}, stop={res.get('done_reason')}, input={res.get('prompt_eval_count')}, output={res.get('eval_count')}, context={config['options']['num_ctx']}.")
  answer=res.get('message',{}).get('content','');usage={k:res.get(k) for k in ['prompt_eval_count','eval_count','done_reason']}
  n=usage['prompt_eval_count'];m=usage['eval_count']
  if type(n) is not int or n<1 or type(m) is not int or m<0:raise CallFailure('missing_usage',f"{config['model']} reported invalid usage: input={n}, output={m}.")
  if n+m>config['options']['num_ctx']:raise CallFailure('context_integrity',f"{config['model']}: input {n} + output {m} exceeds no-shift context {config['options']['num_ctx']}.")
  if res.get('truncated') or res.get('context_shifted'):raise CallFailure('context_integrity','Backend reports discarded context.')
 try:data=json.loads(answer)
 except (ValueError,TypeError) as exc:raise CallFailure('output_contract','Malformed model JSON: '+str(exc),subtype='malformed_json',line=getattr(exc,'lineno',None),column=getattr(exc,'colno',None),repair='Return one complete JSON object matching the schema. Preserve the failed attempt; explicit retry is required.') from None
 try:validate(data)
 except ValueError as exc:raise CallFailure('output_contract','Model JSON violates schema: '+str(exc),subtype='schema',errors=[getattr(exc,'detail',{'detail':str(exc)})]) from None
 return data,answer,usage

def call(prompt,packet,folder,config=None):
 config=config or profile('gpt');validate_profile(config)
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
 request=make_request(prompt,packet,config);save(folder/'request.json',request);save(folder/'packet.json',packet)
 save(folder/'started.json',dict(at=now(),request_hash=digest(request),messages_hash=digest(messages(prompt,packet)),schema_hash=digest(OUTPUT),execution_profile=config))
 started=time.monotonic()
 try:
  if config['provider']=='qwen':
   save(folder/'identity.json',qwen_identity(config));url=config['endpoint'];key=None
  else:url='https://api.openai.com/v1/responses';key=credential()
  raw,request_id=exchange(url,request,key,config['timeout_seconds'])
  (folder/'response.json').write_bytes(raw);res=json.loads(raw)
  # Preserve partial text too; only result.status=completed authorizes recovery.
  if config['provider']=='qwen':partial=res.get('message',{}).get('content','')
  else:partial='\n'.join(c.get('text','') for x in res.get('output',[]) for c in x.get('content',[]) if c.get('type')=='output_text')
  (folder/'answer.txt').write_text(partial)
  data,answer,usage=extract(res,config)
  save(folder/'result.json',dict(status='completed',seconds=round(time.monotonic()-started,3),usage=usage,model=res['model'],provider=config['provider'],request_id=request_id,answer_hash=digest(answer),request_hash=digest(request)))
  return data
 except Exception as exc:
  diag=diagnostic(exc,config)
  if isinstance(exc,urllib.error.HTTPError):
   raw=exc.read();(folder/'http_error.txt').write_text(sanitize(raw.decode('utf-8',errors='replace')))
   low=raw.decode('utf-8',errors='replace').lower()
   if any(x in low for x in ['exceeds the context','context length','context window','context_length_exceeded','context size','exceed_context_size_error']):diag['category']='context_capacity'
   elif exc.code in [401,403]:diag['category']='authentication'
   elif exc.code==429:diag['category']='rate_limit'
   elif any(x in low for x in ['out of memory','allocation failed']):diag['category']='hardware_capacity'
  diag['seconds']=round(time.monotonic()-started,3)
  save(folder/'error.json',diag)
  raise CallFailure(diag['category'],diag['detail'],diagnostic=diag) from None


def sanitize(text):
 text=str(text)
 key=os.environ.get('OPENAI_API_KEY','')
 if key:text=text.replace(key,'[REDACTED]')
 text=re.sub(r'(?i)(bearer\s+)[^\s,;]+',r'\1[REDACTED]',text)
 text=re.sub(r'sk-[A-Za-z0-9_-]+','[REDACTED]',text)
 text=re.sub(r'(?i)(api[_-]?key|authorization|token)([=:\s]+)[^\s,;]+',r'\1\2[REDACTED]',text)
 return text[:4000]

def diagnostic(exc,config=None):
 config=config or {};cause=getattr(exc,'reason',None) or exc.__cause__ or exc
 category=getattr(exc,'category',None)
 if not category:
  if isinstance(cause,ssl.SSLError):category='tls_error'
  elif isinstance(cause,TimeoutError):category='network_timeout'
  elif isinstance(exc,urllib.error.HTTPError):category='http_error'
  elif isinstance(exc,urllib.error.URLError):category='network_error'
  elif isinstance(exc,json.JSONDecodeError):category='provider_protocol'
  else:category='transport_error'
 detail=sanitize(str(cause))
 return dict(status='execution_error',category=category,type=type(exc).__name__,cause_type=type(cause).__name__,detail=detail,
  model=config.get('model'),provider=config.get('provider'),http_status=getattr(exc,'code',None),
  context=config.get('options',{}).get('num_ctx'),metadata=getattr(exc,'metadata',{}),
  recovery='Inspect the preserved attempt and correct configuration/transport or output-contract cause. Use an explicit retry with a reason for a new attempt; no automatic resampling.')
