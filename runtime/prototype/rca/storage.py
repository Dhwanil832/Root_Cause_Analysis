import json,hashlib,datetime,os,tempfile
from pathlib import Path

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix=p.name+'.',dir=p.parent)
 try:
  with os.fdopen(fd,'w') as f:json.dump(x,f,indent=2,ensure_ascii=False);f.write('\n');f.flush();os.fsync(f.fileno())
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def event(state,kind,**data):
 state['events'].append(dict(seq=len(state['events'])+1,at=now(),kind=kind,**data))
def initial(description):
 return dict(description=description,sources={},source_revision=0,ledger={},history=[],events=[],queue=[dict(id='initial',kind='intake',tag='',focus='Understand the focal incident, scope and immediate ambiguities.',target_ids=[])],completed_jobs=[],calls=[],feedback=None,phase='ready',last_decision='',proposals=[])
