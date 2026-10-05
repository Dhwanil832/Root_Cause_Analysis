import json,re,math,copy
from pathlib import Path
from .storage import digest,event
from . import freshness

def extract(path):
 path=Path(path);ext=path.suffix.lower();raw=path.read_bytes()
 if ext=='.json':
  data=json.loads(raw)
  if isinstance(data,dict) and 'sections' in data:
   content='\n\n'.join(f"{x.get('id','')} {x.get('heading','')}\n{x.get('text','')}" for x in data['sections'])
   return data.get('id'),data.get('title',path.name),content,data.get('revision','0'),data.get('kind','record')
  return None,path.name,json.dumps(data,ensure_ascii=False,indent=2),'0','record'
 if ext in ['.txt','.md']:return None,path.name,raw.decode('utf-8'),'0','record'
 if ext=='.pdf':
  try:from pypdf import PdfReader
  except ImportError:raise ValueError('PDF support requires pypdf; use the documented bundled Python or upload text.') from None
  parts=[f'Page {i+1}\n{p.extract_text() or ""}' for i,p in enumerate(PdfReader(path).pages)]
  if not any(len(x.strip())>15 for x in parts):raise ValueError('No usable PDF text. OCR is not available; this is an extraction failure, not absent evidence.')
  return None,path.name,'\n\n'.join(parts),'0','record'
 raise ValueError('Supported uploads: JSON, TXT, MD, text-based PDF.')

def add(state,path=None,request_id=None,answer=None,source_id=None,corrects=None):
 state=copy.deepcopy(state)
 if request_id is not None and (request_id not in state['ledger'] or state['ledger'][request_id]['record']['kind']!='request'):raise ValueError('Unknown evidence request')
 if path:
  original_id,title,content,revision,kind=extract(path)
  sid=source_id or original_id or 'DOC_'+digest(dict(title=title,content=content))[:12]
 else:
  if not answer or not answer.strip():raise ValueError('An answer or document is required.')
  title='User response'+(' to '+request_id if request_id else ' / unsolicited information');content=answer;revision='0';kind='user_testimony';sid=source_id or 'USER_'+digest(dict(text=answer,request=request_id))[:12]
 if corrects:
  if corrects not in state['sources']:raise ValueError('Correction source ID not found')
  sid=corrects
 old=state['sources'].get(sid)
 if old:
  if old['content']==content:
   if request_id and request_id not in old['request_ids']:
    old['request_ids'].append(request_id);state['source_revision']+=1;event(state,'evidence_attached',source_id=sid,request_id=request_id)
    return state,sid,True
   return state,sid,False
  if not corrects:raise ValueError('Source ID already exists with different content; use explicit --corrects.')
 version=old['version']+1 if old else 1
 state['sources'][sid]=dict(id=sid,title=title,content=content,revision=revision,version=version,kind=kind,request_ids=sorted(set((old or {}).get('request_ids',[])+([request_id] if request_id else []))),hash=digest(content),origin_name=Path(path).name if path else 'user_input')
 state['source_revision']+=1
 if old:
  event(state,'source_corrected',source_id=sid,previous=old,new_version=version)
  state.setdefault('source_changes',{})[sid]=dict(source_id=sid,previous_version=old['version'],current_version=version,previous_content=old['content'],current_content=content,request_ids=state['sources'][sid]['request_ids'])
  impacted={rid for rid,item in state['ledger'].items() if sid in item['record']['sources']}
  freshness.invalidate(state,impacted,dict(kind='source_corrected',source_id=sid,previous_version=old['version'],current_version=version))
 else:event(state,'source_received',source_id=sid,request_id=request_id,kind_of_source=kind)
 return state,sid,True

def tokens(s):return set(re.findall(r'[a-z0-9]+',s.lower()))-{'the','and','of','to','for','a','in','or','with','from','as','is','was','on','at','an','by','be'}
def search(state,request):
 query=' '.join([request['claim'],request['asset'],request['window'],*request['fields']]);terms=tokens(query);docs=list(state['sources'].values());ranked=[]
 for d in docs:
  dt=tokens(d['title']+' '+d['content']);overlap=terms&dt
  score=sum(math.log(1+len(docs)/(1+sum(t in tokens(x['title']+' '+x['content']) for x in docs))) for t in overlap)
  linked=request['id'] in d['request_ids']
  if overlap or linked:ranked.append((score+(100 if linked else 0),d))
 ranked.sort(key=lambda v:(-v[0],v[1]['id']))
 # Full matched documents are returned. No silent top-k exclusion on this prototype.
 return dict(query=query,collection_revision=state['source_revision'],searched_ids=sorted(state['sources']),hits=[dict(source=d,lexical_score=round(score,3)) for score,d in ranked],limitation='Lexical retrieval; a search miss is not proof that information does not exist. No OCR or web lookup performed.')
