import copy,json,fcntl
from pathlib import Path
from contextlib import contextmanager
from .storage import read,save,digest,event,initial
from . import controller,documents,provider,prompts

@contextmanager
def lock(case):
 case=Path(case);case.mkdir(parents=True,exist_ok=True)
 with (case/'.lock').open('a') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RuntimeError('This case is already running. Try again after the current step.') from None
  try:yield
  finally:fcntl.flock(f,fcntl.LOCK_UN)

def statepath(case):return Path(case)/'state.json'
def create(case,description,paths):
 case=Path(case)
 with lock(case):
  if statepath(case).exists():raise ValueError('Case exists; choose a new directory.')
  state=initial(description)
  for path in paths:state,_,_=documents.add(state,path=path)
  event(state,'case_created',initial_source_ids=sorted(state['sources']))
  save(statepath(case),state)
 return state

def signature(state,job):
 targets={rid:state['ledger'].get(rid) for rid in sorted(job['target_ids'])}
 if job['kind']=='evidence':
  targets={rid:{k:item['record'][k] for k in ['claim','asset','window','fields']} for rid,item in targets.items() if item}
 return digest(dict(kind=job['kind'],tag=job['tag'].strip().lower(),targets=targets,source_revision=state['source_revision']))

def enqueue(state,job):
 if job['kind'] not in ['lead','intake','specialist','evidence','assessor']:raise ValueError('Unknown job kind')
 if any(x not in state['ledger'] for x in job['target_ids']):return False,'unknown_target'
 if job['kind']=='evidence':
  if len(job['target_ids'])!=1:return False,'evidence_needs_one_request'
  r=state['ledger'][job['target_ids'][0]]['record']
  if r['kind']!='request' or r['status'] not in ['searching','partial']:return False,'request_not_approved_for_search'
 if job['kind']=='assessor':
  existing=next((q for q in state['queue'] if q['kind']=='assessor'),None)
  if existing:
   existing['target_ids']=sorted(set(existing['target_ids']+job['target_ids']))
   if job['focus'] not in existing['focus']:existing['focus']+='; '+job['focus']
   event(state,'assessment_coalesced',job_id=existing['id'],target_ids=existing['target_ids'])
   return True,'coalesced_pending_assessment'
 sig=signature(state,job)
 if job['kind'] not in ['lead','intake'] and any(x['signature']==sig for x in state['completed_jobs']):return False,'already_completed_at_current_evidence_and_target_versions'
 if any(signature(state,x)==sig for x in state['queue']):return False,'already_queued'
 state['queue'].append(dict(job,id=digest(dict(job=job,event_count=len(state['events'])))[:16]));return True,None

def lead_job():return dict(kind='lead',tag='',focus='Review completed proposals/evidence, update the board and select the next immediately useful work.',target_ids=[])

def ensure_upstream_review(state):
 """One explicit origin review per supported premise version/evidence revision.

 This schedules a decision, not a causal finding or mandatory infinite expansion.
 """
 if state['queue'] or state.get('pending_call'):return False
 inputs={rid for item in state['ledger'].values() if controller.active(item) and item['record']['kind']=='edge' and item['record']['status'] not in ['refuted','withdrawn'] for rid in item['record']['from_ids']}
 keys={rid:digest(dict(record=item['record'],source_revision=state['source_revision'])) for rid,item in state['ledger'].items() if rid in inputs and controller.active(item) and not item.get('stale') and item.get('review')!='human_rejected' and item['record']['kind']=='node' and item['record']['status']=='supported'}
 pending={rid:key for rid,key in keys.items() if state.get('upstream_reviews',{}).get(rid)!=key}
 if not pending:return False
 enqueue(state,dict(kind='lead',tag='upstream_review',focus='Stopping review: for EACH targeted supported causal premise, explicitly decide whether its origin is already explained by the board, requires a scoped upstream specialist, is blocked by an identified evidence boundary, or is context/out of scope with a reason. Schedule immediately useful upstream work where justified. Review prior completed work before requesting anything. An unknown sibling mechanism does not close independent upstream branches. This is a coverage review, not an instruction to invent origins or repeat unavailable requests.',target_ids=sorted(pending),review_keys=pending))
 event(state,'upstream_review_scheduled',target_ids=sorted(pending));state['phase']='ready';return True

def submit(case,path=None,request_id=None,answer=None,source_id=None,corrects=None):
 with lock(case):
  state=read(statepath(case));state,sid,changed=documents.add(state,path,request_id,answer,source_id,corrects)
  if changed:
   # Fresh evidence can affect independent branches too; assessor receives collection and full ledger.
   enqueue(state,dict(kind='assessor',tag='',focus='Assess newly submitted evidence '+sid+' and its implications; update affected judgments/requests and retain independent findings.',target_ids=[request_id] if request_id else []))
   state['phase']='ready'
  save(statepath(case),state)
 return sid,changed

def review(case,rid,ver,decision,note):
 with lock(case):
  s=read(statepath(case));item=s['ledger'].get(rid)
  if not item or item['version']!=ver:raise ValueError('Record missing or version changed; inspect current record before review.')
  if item['record']['kind']=='request' or item.get('stale') or not controller.active(item):raise ValueError('Only active fresh physical proposals can receive semantic review.')
  if decision not in ['approved','rejected']:raise ValueError('Review must be approved or rejected.')
  if not note.strip():raise ValueError('A reviewer note is required.')
  item['review']='human_'+decision;event(s,'human_review',record_id=rid,version=ver,decision=decision,note=note)
  if decision=='rejected':
   impacted={rid}
   for _ in range(len(s['ledger'])):
    more={key for key,x in s['ledger'].items() if set(x['record']['depends_on']+x['record']['from_ids']+([x['record']['to_id']] if x['record']['to_id'] else []))&impacted}
    if more<=impacted:break
    impacted|=more
   for key in impacted-{rid}:
    s['ledger'][key]['stale']=True
    if s['ledger'][key]['record']['kind']!='request':s['ledger'][key]['review']='pending_human'
   enqueue(s,lead_job());s['phase']='ready'
  save(statepath(case),s)

def packet(state,job):
 runtime_dir=Path(__file__).resolve().parent
 runtime_hash=digest({x.name:x.read_text() for x in sorted(runtime_dir.glob('*.py'))})
 p=dict(runtime_fingerprint=runtime_hash,incident=state['description'],assignment=job,source_revision=state['source_revision'],ledger=state['ledger'],recent_proposals=state['proposals'],recent_calls=state['calls'][-8:],completed_jobs=state['completed_jobs'],queued_jobs=state['queue'],feedback=state['feedback'])
 if job['kind']=='evidence':
  r=state['ledger'][job['target_ids'][0]]['record'];p['retrieval']=documents.search(state,r);p['sources']=[x['source'] for x in p['retrieval']['hits']]
 else:p['sources']=list(state['sources'].values())
 return p

def apply_result(state,job,data,callpath,sig):
 role=job['kind'];ops=data['operations']
 if state.get('pending_call',{}).get('source_revision',state['source_revision'])!=state['source_revision']:
  state['proposals'].append(dict(role=role,assignment=job,output=data,call_path=callpath,stale_context=True))
  state['feedback']={'accepted':False,'reason':'source_changed_while_call_pending; reassess from current sources'}
  state['calls'].append(dict(role=role,job_id=job['id'],path=callpath,decision=data['decision'],validation=state['feedback']))
  state.pop('pending_call',None);enqueue(state,lead_job());state['phase']='ready'
  event(state,'stale_call_held',call_path=callpath)
  return state,state['feedback']
 if role=='evidence' and any(op['record']['id'] not in job['target_ids'] or op['action']!='revise' for op in ops):
  validation={'accepted':False,'operations':len(ops),'reason':'evidence_can_only_revise_assigned_request'}
 elif role in ['specialist','assessor']:
  state['proposals'].append(dict(role=role,assignment=job,output=data,call_path=callpath));validation={'accepted':None,'reason':'held_for_lead_review','operations':len(ops)}
 else:
  state,validation=controller.apply(state,ops,role)
 if role=='lead' and validation['accepted']:
  if job.get('tag')=='upstream_review':
   state.setdefault('upstream_reviews',{}).update(job.get('review_keys',{}))
   event(state,'upstream_review_recorded',target_ids=job['target_ids'],call_path=callpath,decision=data['decision'])
  state['proposals']=[]
  dispatch=[]
  for proposed in data['next_work']:
   accepted,reason=enqueue(state,proposed);dispatch.append(dict(job=proposed,accepted=accepted,reason=reason))
  validation['dispatch']=dispatch
 if role=='intake':
  state['proposals'].append(dict(role='intake',assignment=job,output=data,call_path=callpath));enqueue(state,lead_job())
 if role=='evidence':
  state['proposals'].append(dict(role='evidence',assignment=job,output=data,call_path=callpath,validation=validation))
  if validation['accepted']:enqueue(state,dict(kind='assessor',tag='',focus='Assess retrieved evidence and coverage for '+','.join(job['target_ids'])+'; do not assume receipt proves a causal link.',target_ids=job['target_ids']))
 state['feedback']=validation;state['last_decision']=data['decision']
 state['completed_jobs'].append(dict(kind=role,tag=job['tag'],target_ids=job['target_ids'],signature=sig,source_revision=state['source_revision'],call_path=callpath))
 state['calls'].append(dict(role=role,job_id=job['id'],path=callpath,decision=data['decision'],validation=validation))
 event(state,'model_step',role=role,job_id=job['id'],call_path=callpath,validation=validation)
 if not state['queue'] and role!='lead':enqueue(state,lead_job())
 if role=='lead' and not validation['accepted']:
  # Leave precise feedback for a deliberate next resume, never claim a partial explanation is complete.
  enqueue(state,lead_job());state['phase']='needs_attention'
 elif state['queue']:state['phase']='ready'
 else:state['phase']=data['disposition'] if data['disposition'] in ['waiting','partial'] else 'needs_attention'
 state.pop('pending_call',None)
 if role=='lead' and validation['accepted']:ensure_upstream_review(state)
 return state,validation

def run(case,max_calls=16,client=provider.call):
 if max_calls<1:raise ValueError('max_calls must be positive; this is a per-run resource limit, not a question quota.')
 case=Path(case)
 with lock(case):
  state=read(statepath(case));completed=0
  ensure_upstream_review(state)
  while (state['queue'] or state.get('pending_call')) and completed<max_calls:
   if state.get('pending_call'):
    pending=state['pending_call'];job=pending['job'];folder=case/pending['path'];sig=pending['signature']
    if not (folder/'result.json').exists() or read(folder/'result.json').get('status')!='completed':
     state['phase']='execution_error';save(statepath(case),state);raise RuntimeError('Unfinished/failed call preserved. Inspect pending_call; no automatic resampling.')
    data=json.loads((folder/'answer.txt').read_text())
   else:
    job=state['queue'].pop(0);sig=signature(state,job)
    if job['kind'] not in ['lead','intake'] and any(x['signature']==sig for x in state['completed_jobs']):
     event(state,'duplicate_job_skipped',job=job);continue
    if job['kind']=='evidence':
     r=state['ledger'].get(job['target_ids'][0],{}).get('record',{})
     if r.get('status') not in ['searching','partial']:
      event(state,'obsolete_evidence_job_skipped',job=job);continue
    folder=case/'calls'/f'{len(state["calls"])+1:04d}_{job["kind"]}'
    p=packet(state,job);state['pending_call']=dict(job=job,path=str(folder.relative_to(case)),signature=sig,packet_hash=digest(p),source_revision=state['source_revision']);save(statepath(case),state)
    try:data=client(prompts.prompt(job['kind']),p,folder)
    except Exception:
     state['phase']='execution_error';save(statepath(case),state);raise
    if job['kind']=='evidence':save(folder/'search.json',p['retrieval'])
   state,validation=apply_result(state,job,data,str(folder.relative_to(case)),sig)
   save(folder/'validation.json',validation);save(folder/'state_after.json',state);save(statepath(case),state)
   completed+=1
   print(json.dumps(dict(call=len(state['calls']),role=job['kind'],phase=state['phase'],validation=validation['reason'],queue=len(state['queue'])),ensure_ascii=False),flush=True)
   if state['phase']=='needs_attention':break
  if state['queue'] and completed>=max_calls:state['phase']='budget_paused';event(state,'operational_pause',reason='per_invocation_call_budget',completed=completed)
  if not state['queue'] and state['phase']=='ready':state['phase']='needs_attention'
  save(statepath(case),state)
 return state


def reapply_last(case,reason):
 """Explicit structural repair, exact saved answer; not a model retry or gold edit."""
 case=Path(case)
 with lock(case):
  s=read(statepath(case));last=s['calls'][-1]
  if last['role']!='lead' or last['validation']['accepted'] is not False or s.get('pending_call'):raise ValueError('Only the latest rejected lead batch can be explicitly reapplied.')
  folder=case/last['path'];request=read(folder/'request.json');p=json.loads(request['input'][1]['content'])
  if p['source_revision']!=s['source_revision'] or p['ledger']!=s['ledger']:raise ValueError('Case evidence/ledger changed; reassessment is required instead of replay.')
  data=json.loads((folder/'answer.txt').read_text());updated,v=controller.apply(s,data['operations'],'lead')
  if not v['accepted']:raise ValueError('Saved batch still rejected: '+v['reason'])
  updated['queue']=[q for q in updated['queue'] if q['kind']!='lead'];updated['proposals']=[]
  dispatch=[]
  for job in data['next_work']:
   ok,why=enqueue(updated,job);dispatch.append(dict(job=job,accepted=ok,reason=why))
  v['dispatch']=dispatch;updated['feedback']=v;updated['last_decision']=data['decision'];updated['phase']='ready' if updated['queue'] else data['disposition']
  event(updated,'saved_response_reapplied',call_path=last['path'],operator_reason=reason,original_rejection=last['validation'],new_validation=v)
  updated['calls'][-1]['reapplication']=dict(reason=reason,validation=v)
  save(folder/'reapplication.json',dict(reason=reason,validation=v,state_after=updated));save(statepath(case),updated)
  return v
