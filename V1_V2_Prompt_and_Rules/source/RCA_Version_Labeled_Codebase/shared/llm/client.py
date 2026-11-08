"""Real OpenAI-compatible HTTP transport for OpenRouter/OpenAI/Ollama.

No silent fixture fallback. Credentials are read from environment and never
recorded in output. An HTTP completion is not a certification of model quality.
"""
from __future__ import annotations
from dataclasses import dataclass
import json,os,re,time,urllib.request,urllib.error

@dataclass
class CallRecord:
    task:str
    model:str
    provider:str
    actual_call_performed:bool
    latency_seconds:float
    tokens:dict
    output:dict

class ModelFailure(RuntimeError):pass

PROVIDER_URLS={
    'openrouter':'https://openrouter.ai/api/v1',
    'openai':'https://api.openai.com/v1',
    'ollama':'http://localhost:11434/v1',
    'compatible':'',
}
PROVIDER_KEYS={'openrouter':('OPENROUTER_API_KEY','RCA_LLM_API_KEY'),
    'openai':('OPENAI_API_KEY','RCA_LLM_API_KEY'),
    'ollama':('RCA_LLM_API_KEY',),
    'compatible':('RCA_LLM_API_KEY',)}

def parse_json(text):
    if isinstance(text,list):text=''.join(item.get('text','') for item in text if isinstance(item,dict))
    if not isinstance(text,str) or not text.strip():
        raise ValueError('No model message content; reasoning-only response is not a valid structured update')
    t=text.strip()
    try:
        parsed=json.loads(t)
        if isinstance(parsed,dict):return parsed
    except (ValueError,TypeError):pass
    t=re.sub(r'^```(?:json)?\s*|\s*```$', '',t,flags=re.I).strip()
    try:
        parsed=json.loads(t)
        if isinstance(parsed,dict):return parsed
    except (ValueError,TypeError):pass
    # Be tolerant of brief explanatory prefixes/suffixes while preserving strict object shape.
    dec=json.JSONDecoder()
    for i,c in enumerate(t):
        if c=='{':
            try:
                parsed,j=dec.raw_decode(t[i:])
                if isinstance(parsed,dict):return parsed
            except ValueError:continue
    raise ValueError('No complete JSON object in model response')

class ChatCompletionsModel:
    def __init__(self,provider,model,base_url=None,api_key=None,timeout=120,
                 response_format='json_object',retries=1):
        if provider not in PROVIDER_URLS:raise ModelFailure(f'Unknown provider {provider}')
        self.provider=provider
        self.model=model
        self.base_url=(base_url or os.getenv('RCA_LLM_BASE_URL') or PROVIDER_URLS[provider]).rstrip('/')
        if not self.base_url.startswith(('http://','https://')):raise ModelFailure('Provider base URL required')
        self.api_key=api_key or next((os.environ[x] for x in PROVIDER_KEYS[provider] if os.getenv(x)),None)
        self.timeout=float(timeout)
        self.response_format=response_format
        self.retries=int(retries)
        self.calls=[]
        self.http_attempts=0
        if not model or not isinstance(model,str):raise ModelFailure('Set an explicit provider model identifier')
        if not self.api_key and not self.base_url.startswith(('http://127.0.0.1:','http://localhost:')):
            raise ModelFailure('No API credential configured; set OPENROUTER_API_KEY or RCA_LLM_API_KEY')

    def ask(self,task,system,payload):
        base_messages=[{'role':'system','content':system},
              {'role':'user','content':json.dumps(payload,ensure_ascii=False,default=str)}]
        began=time.monotonic()
        last_error=None
        for n in range(self.retries+1):
            msgs=list(base_messages)
            if n:
                msgs.append({'role':'user','content':'Previous response failed JSON validation. Return one complete, valid JSON object conforming to the requested schema. No markdown.'})
            body={'model':self.model,'messages':msgs}
            if self.response_format=='json_object':body['response_format']={'type':'json_object'}
            headers={'Content-Type':'application/json','User-Agent':'RCA-Research-Prototype/0.4',
                     'X-RCA-Task':task}
            if self.api_key:headers['Authorization']='Bearer '+self.api_key
            if self.provider=='openrouter':headers['X-Title']='Progressive RCA Research Prototype'
            req=urllib.request.Request(self.base_url+'/chat/completions',data=json.dumps(body).encode('utf8'),headers=headers,method='POST')
            self.http_attempts+=1
            try:
                with urllib.request.urlopen(req,timeout=self.timeout) as response:
                    received=json.loads(response.read(5_000_000))
                msg=received['choices'][0]['message']
                parsed=parse_json(msg.get('content'))
                self.calls.append(CallRecord(task,self.model,self.provider,True,
                     round(time.monotonic()-began,3),received.get('usage',{}),parsed))
                return parsed
            except urllib.error.HTTPError as e:
                detail=e.read(900).decode('utf8','replace')
                last_error=f'HTTP {e.code}: {detail}'
                # 400 errors (bad response_format etc.) must be fixed in config.
                if e.code not in (408,429,500,502,503,504) or n==self.retries:break
                time.sleep(min(2**n,3))
            except (urllib.error.URLError,TimeoutError,OSError) as e:
                last_error=f'{type(e).__name__}: {e}'
                if n==self.retries:break
                time.sleep(min(2**n,3))
            except (ValueError,KeyError,IndexError,TypeError) as e:
                last_error=f'Invalid model response: {e}'
                if n==self.retries:break
        raise ModelFailure(f'{self.provider}/{self.model} call failed after {self.http_attempts} HTTP attempts: {last_error}')
