import json,os,ssl,time,urllib.request
from pathlib import Path
from .storage import save,digest,now
from .schema import OUTPUT
MODEL='gpt-5.5-2026-04-23'

def credential():
 key=os.environ.get('OPENAI_API_KEY','').strip()
 p=Path(__file__).resolve().parents[2]/'.env.local'
 if not key and p.exists():
  for line in p.read_text().splitlines():
   if line.strip().startswith('OPENAI_API_KEY='):key=line.strip().split('=',1)[1].strip().strip('\"\'')
 if not key or key=='...' or any(c.isspace() for c in key):raise RuntimeError('OPENAI_API_KEY is not configured correctly.')
 return key
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def make_request(prompt,packet):
 return dict(model=MODEL,input=[dict(role='system',content=prompt),dict(role='user',content=json.dumps(packet,ensure_ascii=False))],reasoning={'effort':'medium'},max_output_tokens=32768,store=False,stream=False,truncation='disabled',text={'format':{'type':'json_schema','name':'rca_step','strict':True,'schema':OUTPUT}})

def call(prompt,packet,folder):
 key=credential();folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
 request=make_request(prompt,packet);save(folder/'request.json',request);save(folder/'started.json',{'at':now(),'request_hash':digest(request)})
 req=urllib.request.Request('https://api.openai.com/v1/responses',data=json.dumps(request).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
 started=time.monotonic()
 try:
  cafile='/etc/ssl/cert.pem' if Path('/etc/ssl/cert.pem').exists() else None
  opener=urllib.request.build_opener(NoRedirect,urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=cafile)))
  with opener.open(req,timeout=600) as response:raw=response.read();request_id=response.headers.get('x-request-id')
  (folder/'response.json').write_bytes(raw);res=json.loads(raw)
  if res.get('status')!='completed' or res.get('model')!=MODEL:raise ValueError('Incomplete response or changed model')
  parts=[c['text'] for x in res.get('output',[]) if x.get('type')=='message' for c in x.get('content',[]) if c.get('type')=='output_text']
  answer='\n'.join(parts);(folder/'answer.txt').write_text(answer);data=json.loads(answer)
  save(folder/'result.json',dict(status='completed',seconds=round(time.monotonic()-started,3),usage=res['usage'],model=res['model'],request_id=request_id,answer_hash=digest(answer),request_hash=digest(request)))
  return data
 except Exception as exc:
  save(folder/'error.json',dict(status='execution_error',type=type(exc).__name__,http_status=getattr(exc,'code',None),seconds=round(time.monotonic()-started,3)))
  raise RuntimeError('Model call stopped; saved error metadata. No automatic retry or semantic substitute.') from None
