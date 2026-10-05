import copy,json,fcntl
from pathlib import Path
from contextlib import contextmanager
from .storage import read,save,digest,event,initial
from . import controller,documents,provider,prompts,schema,freshness
from .contract import VERSION, ContractError

@contextmanager
def lock(case):
 case=Path(case);case.mkdir(parents=True,exist_ok=True)
 with (case/'.lock').open('a') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RuntimeError('This case is already running. Submit or review after the current run pauses; its lock covers the whole invocation.') from None
  try:yield
  finally:fcntl.flock(f,fcntl.LOCK_UN)

def fingerprint():
 root=Path(__file__).resolve().parent
 return digest(dict(files={x.name:x.read_text() for x in sorted(root.glob('*.py'))},prompts={r:prompts.prompt(r) for r in prompts.ROLES}))

def statepath(case):return Path(case)/'state.json'

def check_runtime(state):
 if state.get('runtime_contract')!=VERSION or state.get('runtime_fingerprint')!=fingerprint():
  raise ValueError('Case belongs to a different runtime contract. Preserve the historical case and initialize a new case for this repaired harness.')

def create(case,description,paths,model_provider='gpt'):
 case=Path(case)
 with lock(case):
  if statepath(case).exists():raise ValueError('Case exists; choose a new directory.')
  state=initial(description);state['execution_profile']=provider.profile(model_provider)
  state['execution_profile_hash']=digest(state['execution_profile'])
  state['runtime_contract']=VERSION;state['runtime_fingerprint']=fingerprint()
  for path in paths:state,_,_=documents.add(state,path=path)
  event(state,'case_created',initial_source_ids=sorted(state['sources']))
  save(statepath(case),state)
 return state

def signature(state,job):
 targets={rid:state['ledger'].get(rid) for rid in sorted(job['target_ids'])}
 if job['kind']=='evidence':
  targets={rid:{k:item['record'][k] for k in ['claim','asset','window','fields']} for rid,item in targets.items() if item}
 identity=dict(kind=job['kind'],tag=job['tag'].strip().lower(),targets=targets,source_revision=state['source_revision'])
 # Evidence identity is the acquisition scope, not wording/status of a search.
 # V2 specialist/assessor identities retain the actual question being asked.
 if job['kind']!='evidence':identity.update(signature_version=2,focus=controller.norm(job['focus']))
 return digest(identity)

def completed(state,sig):
 return any(x['signature']==sig and x.get('accepted') is not False for x in state['completed_jobs'])

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
 if job['kind'] not in ['lead','intake'] and completed(state,sig):return False,'already_completed_at_current_evidence_and_target_versions'
 if any(signature(state,x)==sig for x in state['queue']):return False,'already_queued'
 state['queue'].append(dict(job,id=digest(dict(job=job,event_count=len(state['events'])))[:16]));return True,None

def lead_job():return dict(kind='lead',tag='',focus='Review completed proposals/evidence, update the board and select the next immediately useful work.',target_ids=[])

def review_key(state,item):
 # Relevant incoming links may be added/withdrawn without changing this node.
 incoming={rid:x for rid,x in state['ledger'].items() if x['record']['kind']=='edge' and x['record']['to_id']==item['record']['id']}
 rid=item['record']['id']
 requests={key:x for key,x in state['ledger'].items() if x['record']['kind']=='request' and rid in x['record']['depends_on']}
 work=[{'signature':x['signature'],'accepted':x.get('accepted')} for x in state['completed_jobs'] if x.get('kind') in ['specialist','assessor'] and rid in x.get('target_ids',[])]
 return digest(dict(contract=2,item=item,incoming=incoming,requests=requests,work=work,source_revision=state['source_revision']))

def reviewable(item):
 return controller.active(item) and not item.get('stale') and item.get('review')!='human_rejected' and item['record']['kind']=='node' and item['record']['status']=='supported'

def ensure_followup(state):
 """Drain proposal review and stale-record reassessment before origin closure."""
 if state['queue'] or state.get('pending_call'):return False
 if state['proposals']:
  enqueue(state,lead_job());state['phase']='ready';return True
 stale=freshness.outstanding(state)
 if stale:
  job=dict(kind='assessor',tag='dependency_reassessment',target_ids=stale,
   focus='Reassess every targeted stale record against original current sources and typed dependencies. Propose supported, uncertain, refuted, corrected or withdrawn judgments as warranted; do not automatically restore support. For stale requests reassess coverage. Include affected causal links and preserve independent findings. The lead must commit justified reassessments before stopping; explain any inability to resolve a target.')
  accepted,reason=enqueue(state,job)
  if accepted:
   event(state,'reassessment_scheduled',target_ids=stale);state['phase']='ready';return True
  # No silent clean stop and no automatic loop on the same failed assessment.
  state['phase']='needs_attention'
  state['feedback']=dict(accepted=False,committed=False,reason='stale_records_unresolved',
   stale_record_ids=stale,assessment_status=reason,
   repair='The completed assessment/lead review left these records stale. Reassess or retire them with justified operations; no completed-board claim is permitted.')
  event(state,'reassessment_incomplete',target_ids=stale,reason=reason);return False
 return ensure_upstream_review(state)

def ensure_upstream_review(state):
 """One explicit origin review per supported premise version/evidence revision.

 This schedules a decision, not a causal finding or mandatory infinite expansion.
 """
 if state['queue'] or state.get('pending_call'):return False
 keys={rid:review_key(state,item) for rid,item in state['ledger'].items() if reviewable(item)}
 pending={rid:key for rid,key in keys.items() if state.get('upstream_reviews',{}).get(rid)!=key}
 if not pending:return False
 enqueue(state,dict(kind='lead',tag='upstream_review',focus='Stopping review: for EACH targeted supported causal premise, explicitly decide whether its origin is already explained by the board, requires a scoped upstream specialist, is blocked by an identified evidence boundary, or is context/out of scope with a reason. Schedule immediately useful upstream work where justified. Review prior completed work before requesting anything. An unknown sibling mechanism does not close independent upstream branches. This is a coverage review, not an instruction to invent origins or repeat unavailable requests.',target_ids=sorted(pending),review_keys=pending))
 event(state,'upstream_review_scheduled',target_ids=sorted(pending));state['phase']='ready';return True

def validate_upstream(state,job,data,dispatch,defer_stale=False):
 decisions=data['upstream_dispositions'];rid=None;position=None;deferred=[]
 def bad(code):
  ids=[d['target_id'] for d in decisions]
  raise ContractError(code,phase='upstream_review',path='$.upstream_dispositions'+(f'[{position}]' if position is not None else ''),target_id=rid,
   expected_targets=job['target_ids'],actual_targets=ids,missing_targets=sorted(set(job['target_ids'])-set(ids)),
   extra_targets=sorted(set(ids)-set(job['target_ids'])),duplicate_targets=sorted({x for x in ids if ids.count(x)>1}),
   unknown_sources=sorted({x for d in decisions for x in d['source_ids'] if x not in state['sources']}),
   unknown_records=sorted({x for d in decisions for x in d['record_ids'] if x not in state['ledger']}),
   supplied_records={x:state['ledger'].get(x) for d in decisions for x in d['record_ids']},dispatch=dispatch,
   repair='Provide one justified disposition per target. investigate needs accepted dispatched specialist/assessor work; already_explained needs an active fresh supported incoming edge not rejected by a human; blocked needs cited boundary evidence or a fresh linked blocked/awaiting_user/partial request. Withdraw support before no_longer_applicable.')
 if job.get('tag')!='upstream_review' or job['kind']!='lead':
  if decisions:bad('upstream_dispositions_only_for_stopping_review')
  return
 ids=[d['target_id'] for d in decisions]
 if len(ids)!=len(set(ids)) or set(ids)!=set(job['target_ids']):bad('upstream_review_requires_one_disposition_per_target')
 for position,d in enumerate(decisions):
  rid=d['target_id'];item=state['ledger'].get(rid)
  if not d['reason'].strip():bad('upstream_review_requires_reason')
  if set(d['source_ids'])-set(state['sources']) or set(d['record_ids'])-set(state['ledger']):bad('upstream_review_unknown_reference')
  if d['action']=='no_longer_applicable':
   if item and controller.active(item) and item['record']['kind']=='node' and item['record']['status']=='supported' and item.get('review')!='human_rejected':bad('upstream_target_still_supported')
   continue
  stale_target=bool(item and controller.active(item) and item.get('stale') and item['record']['kind']=='node' and item['record']['status']=='supported' and item.get('review')!='human_rejected')
  if not item or (not reviewable(item) and not (defer_stale and stale_target)):bad('upstream_target_no_longer_supported')
  if stale_target:deferred.append(dict(target_id=rid,reason='target_requires_reassessment'))
  if d['action']=='investigate':
   if not any(x['accepted'] and rid in x['job']['target_ids'] and x['job']['kind'] in ['specialist','assessor'] for x in dispatch):bad('upstream_investigate_requires_dispatched_work')
  elif d['action']=='already_explained':
   links=[state['ledger'][x] for x in d['record_ids']]
   supported=[x for x in links if controller.active(x) and x.get('review')!='human_rejected' and x['record']['kind']=='edge' and x['record']['status']=='supported' and x['record']['to_id']==rid]
   if not any(not x.get('stale') for x in supported):
    if defer_stale and supported:deferred.append(dict(target_id=rid,reason='incoming_link_requires_reassessment',record_ids=[x['record']['id'] for x in supported]))
    else:bad('upstream_explained_requires_supported_incoming_link')
  elif d['action']=='blocked':
   requests=[state['ledger'][x] for x in d['record_ids']]
   if not d['source_ids'] and not any(controller.active(x) and not x.get('stale') and x['record']['kind']=='request' and x['record']['status'] in ['blocked','awaiting_user','partial'] and rid in x['record']['depends_on'] for x in requests):bad('upstream_blocked_requires_source_or_linked_open_request')
 # This is structural coverage, never a check that the stated reason is true.
 return deferred

def submit_bundle(case,entries):
 """Validate/extract all entries on a copy; save the bundle once or not at all."""
 with lock(case):
  state=read(statepath(case));check_runtime(state) if state.get('runtime_contract') or state.get('calls') else None
  outcomes=[]
  for entry in entries:
   state,sid,changed=documents.add(state,**entry);outcomes.append(dict(source_id=sid,changed=changed))
   if changed:
    enqueue(state,dict(kind='assessor',tag='',focus='Assess submitted evidence '+sid+' and coverage, corrections and independent branches.',target_ids=[entry['request_id']] if entry.get('request_id') else []))
    state['phase']='ready'
  save(statepath(case),state)
 return outcomes

def submit(case,path=None,request_id=None,answer=None,source_id=None,corrects=None):
 entries=[]
 if answer:entries.append(dict(answer=answer,request_id=request_id,source_id=source_id,corrects=corrects if not path else None))
 if path:entries.append(dict(path=path,request_id=request_id,source_id=source_id,corrects=corrects))
 if not entries:raise ValueError('An answer or document is required.')
 result=submit_bundle(case,entries)[-1]
 return result['source_id'],result['changed']

def review(case,rid,ver,decision,note):
 with lock(case):
  s=read(statepath(case))
  if s.get('runtime_contract') or s.get('calls'):check_runtime(s)
  item=s['ledger'].get(rid)
  if not item or item['version']!=ver:raise ValueError('Record missing or version changed; inspect current record before review.')
  if item['record']['kind']=='request' or item.get('stale') or not controller.active(item):raise ValueError('Only active fresh physical proposals can receive semantic review.')
  if decision not in ['approved','rejected']:raise ValueError('Review must be approved or rejected.')
  if not note.strip():raise ValueError('A reviewer note is required.')
  item['review']='human_'+decision;item['human_review']=dict(decision=decision,note=note,version=ver)
  event(s,'human_review',record_id=rid,version=ver,decision=decision,note=note)
  if decision=='rejected':
   freshness.invalidate(s,{rid},dict(kind='human_rejected',record_id=rid,version=ver),protected={rid})
   enqueue(s,lead_job());s['phase']='ready'
  save(statepath(case),s)

def packet(state,job):
 runtime_hash=fingerprint()
 p=dict(runtime_fingerprint=runtime_hash,incident=state['description'],assignment=job,source_revision=state['source_revision'],ledger=state['ledger'],recent_proposals=state['proposals'],recent_calls=state['calls'][-8:],completed_jobs=state['completed_jobs'],queued_jobs=state['queue'],feedback=state['feedback'])
 p['runtime_contract']=VERSION
 p['source_changes']=state.get('source_changes',{})
 p['reassessment_required']=freshness.outstanding(state)
 p['dependency_relations']={rid:freshness.relations(state['ledger'],item['record']) for rid,item in state['ledger'].items() if controller.active(item)}
 p['upstream_dispositions']=state.get('upstream_dispositions',{})
 if job['kind']=='evidence':
  r=state['ledger'][job['target_ids'][0]]['record'];p['retrieval']=documents.search(state,r);p['sources']=[x['source'] for x in p['retrieval']['hits']]
 else:p['sources']=list(state['sources'].values())
 return p

def apply_result(state,job,data,callpath,sig):
 role=job['kind'];ops=data.get('operations',[])
 try:schema.validate(data)
 except ValueError as e:
  state['feedback']=dict(accepted=False,committed=False,reason='output_schema: '+str(e),errors=[getattr(e,'detail',{'detail':str(e)})]);state['phase']='needs_attention'
  event(state,'output_contract_rejected',call_path=callpath,validation=state['feedback'])
  return state,state['feedback']
 if state.get('pending_call',{}).get('source_revision',state['source_revision'])!=state['source_revision']:
  state['proposals'].append(dict(role=role,assignment=job,output=data,call_path=callpath,stale_context=True))
  state['feedback']={'accepted':False,'reason':'source_changed_while_call_pending; reassess from current sources'}
  state['calls'].append(dict(role=role,job_id=job['id'],path=callpath,decision=data['decision'],validation=state['feedback']))
  state.pop('pending_call',None);enqueue(state,lead_job());state['phase']='ready'
  event(state,'stale_call_held',call_path=callpath)
  return state,state['feedback']
 if role!='lead' and (data['upstream_dispositions'] or (role!='intake' and data['next_work'])):
  validation={'accepted':False,'committed':False,'operations':len(ops),'reason':'worker_cannot_dispatch_or_close_upstream_review','errors':[dict(code='role_output',role=role,assignment_tag=job.get('tag'),forbidden_fields=[k for k in ['next_work','upstream_dispositions'] if data[k] and (k!='next_work' or role!='intake')],expected='Empty arrays for forbidden fields',repair='Keep justified proposed operations; remove forbidden dispatch/review entries. Only a lead upstream_review call can populate upstream_dispositions.')]} 
 elif role=='evidence' and any(op['record']['id'] not in job['target_ids'] or op['action']!='revise' for op in ops):
  validation={'accepted':False,'committed':False,'operations':len(ops),'reason':'evidence_can_only_revise_assigned_request','errors':[dict(code='evidence_scope',path=f'$.operations[{i}]',record_id=op['record']['id'],actual_action=op['action'],expected_action='revise',allowed_ids=job['target_ids']) for i,op in enumerate(ops) if op['record']['id'] not in job['target_ids'] or op['action']!='revise']}
 elif role in ['specialist','assessor']:
  state['proposals'].append(dict(role=role,assignment=job,output=data,call_path=callpath));validation={'accepted':None,'reason':'held_for_lead_review','operations':len(ops)}
 else:
  trial,validation=controller.apply(state,ops,role)
  if validation['accepted']:
   dispatch=[]
   if role=='lead':
    for proposed in data['next_work']:
     accepted,reason=enqueue(trial,proposed);dispatch.append(dispatch_result(trial,proposed,accepted,reason))
   try:
    invalid=[d for d in dispatch if not d['accepted'] and not d['duplicate']]
    if invalid:raise ContractError('dispatch_rejected',phase='dispatch',path='$.next_work',rejected_jobs=invalid,repair='Correct missing targets/request approval; resubmit the batch. No operations or jobs committed.')
    deferred=validate_upstream(trial,job,data,dispatch,defer_stale=True)
    if deferred:validation['upstream_review_deferred']=deferred
   except ValueError as e:validation=dict(accepted=False,operations=len(ops),operations_valid=True,committed=False,reason=str(e),dispatch=dispatch,errors=[getattr(e,'detail',{'code':str(e)})])
   else:
    state=trial
    validation['committed']=True;validation['operations_accepted']=True
    if role=='lead':validation['dispatch']=dispatch
 if role=='lead' and validation['accepted']:
  if job.get('tag')=='upstream_review' and not validation.get('upstream_review_deferred'):
   for d in data['upstream_dispositions']:
    rid=d['target_id'];item=state['ledger'].get(rid)
    if item and reviewable(item):state.setdefault('upstream_reviews',{})[rid]=review_key(state,item)
    state.setdefault('upstream_dispositions',{})[rid]=dict(d,call_path=callpath,source_revision=state['source_revision'])
   event(state,'upstream_review_recorded',target_ids=job['target_ids'],call_path=callpath,dispositions=data['upstream_dispositions'])
  elif validation.get('upstream_review_deferred'):
   event(state,'upstream_review_deferred',call_path=callpath,targets=validation['upstream_review_deferred'])
  state['proposals']=[]
 if role=='intake':
  state['proposals'].append(dict(role='intake',assignment=job,output=data,call_path=callpath));enqueue(state,lead_job())
 if role=='evidence':
  state['proposals'].append(dict(role='evidence',assignment=job,output=data,call_path=callpath,validation=validation))
  if validation['accepted']:enqueue(state,dict(kind='assessor',tag='',focus='Assess retrieved evidence and coverage for '+','.join(job['target_ids'])+'; do not assume receipt proves a causal link.',target_ids=job['target_ids']))
 state['feedback']=validation
 state['last_update']=dict(role=role,decision=data['decision'],accepted=validation['accepted'],committed=validation.get('committed',False),call_path=callpath)
 if validation['accepted'] is True:
  state['last_decision']=('Upstream closure deferred pending reassessment. Model proposal: ' if validation.get('upstream_review_deferred') else '')+data['decision']
 if validation['accepted'] is True:
  for op in ops:
   item=state['ledger'].get(op['record']['id'])
   if item and item['record']['kind']=='request':item['coverage_decision']=data['decision']
 state['completed_jobs'].append(dict(kind=role,tag=job['tag'],focus=job['focus'],target_ids=job['target_ids'],signature=sig,accepted=validation['accepted'],source_revision=state['source_revision'],call_path=callpath))
 state['calls'].append(dict(role=role,job_id=job['id'],path=callpath,decision=data['decision'],validation=validation))
 event(state,'model_step',role=role,job_id=job['id'],call_path=callpath,validation=validation)
 if not state['queue'] and role!='lead':enqueue(state,lead_job())
 if role=='lead' and not validation['accepted']:
  # Leave precise feedback for a deliberate next resume, never claim a partial explanation is complete.
  # Retry the same coverage assignment, never erase its per-target obligations.
  enqueue(state,{k:v for k,v in job.items() if k!='id'});state['phase']='needs_attention'
 elif state['queue']:state['phase']='ready'
 else:state['phase']=data['disposition'] if data['disposition'] in ['waiting','partial'] else 'needs_attention'
 state.pop('pending_call',None)
 if role=='lead' and validation['accepted']:ensure_followup(state)
 return state,validation

def run(case,max_calls=None,client=None,_on_started=None):
 if max_calls is not None and (type(max_calls) is not int or max_calls<1):raise ValueError('max_calls must be a positive integer or None for no call-count cap.')
 case=Path(case)
 with lock(case):
  state=read(statepath(case));check_runtime(state);count=0
  if _on_started:_on_started()
  execution=state.get('execution_profile',provider.profile('gpt'))
  if client is None:
   if state['calls'] and 'execution_profile' not in state:raise ValueError('Historical case uses an older execution profile. Start a new case for the new configuration; preserve the historical result.')
   provider.validate_profile(execution)
   if state.get('execution_profile_hash',digest(execution))!=digest(execution):raise ValueError('Case execution profile changed; create a separate comparison case.')
   # A legacy case had only the GPT adapter. Never silently relabel its calls.
   for previous in state['calls']:
    started_path=case/previous['path']/'started.json'
    old=read(started_path).get('execution_profile',provider.profile('gpt')) if started_path.exists() else provider.profile('gpt')
    if old!=execution:raise ValueError('Cannot mix providers/configurations within a case.')
   client=lambda prompt,p,folder:provider.call(prompt,p,folder,execution)
  ensure_followup(state)
  while (state['queue'] or state.get('pending_call')) and (max_calls is None or count<max_calls):
   if state.get('pending_call'):
    pending=state['pending_call'];job=pending['job'];folder=case/pending['path'];sig=pending['signature']
    if not (folder/'result.json').exists() or read(folder/'result.json').get('status')!='completed':
     state['phase']='execution_error';save(statepath(case),state);raise RuntimeError('Failed attempt preserved. Use inspect-failure, then retry-failed --reason to explicitly authorize a new attempt; a completed saved response recovers through run.')
    answer=(folder/'answer.txt').read_text();result=read(folder/'result.json')
    if 'answer_hash' in result and result['answer_hash']!=digest(answer):raise ValueError('Saved answer hash mismatch; recovery stopped.')
    data=json.loads(answer)
   else:
    job=state['queue'].pop(0);sig=signature(state,job)
    if job['kind'] not in ['lead','intake'] and completed(state,sig):
     event(state,'duplicate_job_skipped',job=job);ensure_followup(state);continue
    if job['kind']=='evidence':
     r=state['ledger'].get(job['target_ids'][0],{}).get('record',{})
     if r.get('status') not in ['searching','partial']:
      event(state,'obsolete_evidence_job_skipped',job=job);ensure_followup(state);continue
    number=state.get('attempt_count',len(state['calls']))+1
    folder=case/'calls'/f'{number:04d}_{job["kind"]}'
    while folder.exists():
     number+=1;folder=case/'calls'/f'{number:04d}_{job["kind"]}'
    state['attempt_count']=number
    p=packet(state,job);state['pending_call']=dict(job=job,path=str(folder.relative_to(case)),signature=sig,packet_hash=digest(p),source_revision=state['source_revision']);save(statepath(case),state)
    try:data=client(prompts.prompt(job['kind']),p,folder)
    except Exception as exc:
     state['last_error']=read(folder/'error.json') if (folder/'error.json').exists() else provider.diagnostic(exc,execution)
     state['last_error'].update(call_path=str(folder.relative_to(case)),role=job['kind'])
     state['phase']='execution_error';event(state,'execution_failed',error=state['last_error']);save(statepath(case),state);raise
    if job['kind']=='evidence':save(folder/'search.json',p['retrieval'])
   state.pop('last_error',None)
   state,validation=apply_result(state,job,data,str(folder.relative_to(case)),sig)
   save(folder/'validation.json',validation);save(folder/'state_after.json',state);save(statepath(case),state)
   count+=1
   print(json.dumps(dict(call=len(state['calls']),role=job['kind'],phase=state['phase'],validation=validation['reason'],queue=len(state['queue'])),ensure_ascii=False),flush=True)
   if state['phase']=='needs_attention':break
  if max_calls is not None and state['queue'] and count>=max_calls and state['phase']!='needs_attention':state['phase']='budget_paused';event(state,'operational_pause',reason='per_invocation_call_budget',completed=count)
  if not state['queue'] and state['phase']=='ready':state['phase']='partial' if state['ledger'] else 'waiting'
  save(statepath(case),state)
 return state


def reapply_last(case,reason):
 """Explicit structural repair, exact saved answer; not a model retry or gold edit."""
 case=Path(case)
 if not reason.strip():raise ValueError('A reapplication reason is required.')
 with lock(case):
  s=read(statepath(case));check_runtime(s)
  if not s['calls']:raise ValueError('No saved response to reapply.')
  last=s['calls'][-1]
  if last['role']!='lead' or last['validation']['accepted'] is not False or s.get('pending_call'):raise ValueError('Only the latest rejected lead batch can be explicitly reapplied.')
  folder=case/last['path'];request=read(folder/'request.json');p=json.loads(request.get('input',request.get('messages'))[1]['content'])
  if p['source_revision']!=s['source_revision'] or p['ledger']!=s['ledger']:raise ValueError('Case evidence/ledger changed; reassessment is required instead of replay.')
  answer=(folder/'answer.txt').read_text();result=read(folder/'result.json')
  if result.get('answer_hash')!=digest(answer):raise ValueError('Saved answer hash mismatch; reapplication stopped.')
  data=json.loads(answer);schema.validate(data);updated,v=controller.apply(s,data['operations'],'lead')
  if not v['accepted']:raise ValueError('Saved batch still rejected: '+v['reason'])
  # Older responses can be replayed only for the old non-review contract.
  if p['assignment'].get('tag')=='upstream_review':raise ValueError('Stopping-review outputs require their full atomic review contract; resume the assignment instead.')
  if 'upstream_dispositions' in data:schema.validate(data);validate_upstream(updated,p['assignment'],data,[])
  updated['queue']=[q for q in updated['queue'] if q['kind']!='lead'];updated['proposals']=[]
  dispatch=[]
  for job in data['next_work']:
   ok,why=enqueue(updated,job);dispatch.append(dispatch_result(updated,job,ok,why))
  if any(not x['accepted'] and not x['duplicate'] for x in dispatch):raise ValueError('Saved dispatch still rejected: '+json.dumps(dispatch))
  v['committed']=True
  updated['last_update']=dict(role='lead',decision=data['decision'],accepted=True,committed=True,call_path=last['path'])
  v['dispatch']=dispatch;updated['feedback']=v;updated['last_decision']=data['decision'];updated['phase']='ready' if updated['queue'] else data['disposition']
  event(updated,'saved_response_reapplied',call_path=last['path'],operator_reason=reason,original_rejection=last['validation'],new_validation=v)
  updated['calls'][-1]['reapplication']=dict(reason=reason,validation=v)
  ensure_followup(updated)
  save(folder/'reapplication.json',dict(reason=reason,validation=v,state_after=updated));save(statepath(case),updated)
  return v


def dispatch_result(state,job,accepted,reason):
 duplicate=reason in ['already_queued','already_completed_at_current_evidence_and_target_versions']
 result=dict(job=job,accepted=accepted,reason=reason,duplicate=duplicate)
 if not accepted:
  result['unknown_targets']=[rid for rid in job['target_ids'] if rid not in state['ledger']]
  result['target_statuses']={rid:state['ledger'].get(rid,{}).get('record',{}).get('status') for rid in job['target_ids']}
  sig=signature(state,job)
  result['matching_queued_jobs']=[q['id'] for q in state['queue'] if signature(state,q)==sig]
  result['matching_completed_calls']=[x.get('call_path') for x in state['completed_jobs'] if x['signature']==sig and x.get('accepted') is not False]
  result['repair']='Reuse the identified queued/completed work; change the actual evidence/question only when justified.' if duplicate else 'Use existing targets; evidence jobs require exactly one searching/partial request. Correct approval and dispatch in the same batch.'
 return result

def inspect_failure(case):
 state=read(statepath(case));pending=state.get('pending_call');error=state.get('last_error')
 if pending:
  path=Path(case)/pending['path']
  if (path/'error.json').exists():error=read(path/'error.json')
 return dict(phase=state['phase'],pending_call=pending,error=error,feedback=state.get('feedback'),
  recovery='run recovers an intact completed result without another model call. retry-failed --reason schedules a new attempt for an incomplete/failed result; the original remains preserved.',
  failed_attempts=state.get('failed_attempts',[]))

def retry_failed(case,reason):
 if not reason.strip():raise ValueError('A recovery reason is required.')
 with lock(case):
  s=read(statepath(case));check_runtime(s);pending=s.get('pending_call')
  if not pending:raise ValueError('No failed pending attempt. Resume a rejected lead assignment with run.')
  folder=Path(case)/pending['path']
  if (folder/'result.json').exists() and read(folder/'result.json').get('status')=='completed':raise ValueError('A completed result exists: use run for exact recovery; do not resample it.')
  archived=dict(pending,reason=reason,error=inspect_failure(case)['error'])
  s.setdefault('failed_attempts',[]).append(archived)
  # The queued attempt is fresh work on current evidence, never an edited answer.
  job={k:v for k,v in pending['job'].items() if k!='id'}
  s.pop('pending_call');s.pop('last_error',None)
  s['feedback']=dict(accepted=False,reason='previous_attempt_failed',errors=[archived['error'] or {'detail':'Interrupted attempt without a recorded diagnostic; inspect its saved artifacts.'}],repair='Correct the reported output-contract error if applicable. This is a separately recorded retry on current evidence.')
  accepted,why=enqueue(s,job)
  if not accepted:raise ValueError('Retry no longer applicable: '+str(why)+'. Inspect current evidence and queue.')
  s['phase']='ready';event(s,'retry_authorized',original_attempt=pending['path'],operator_reason=reason,new_attempt_uses_current_evidence=True)
  save(statepath(case),s)
 return dict(scheduled=True,original_attempt=pending['path'],model_calls=0,reason=reason)

def view_state(case):
 s=read(statepath(case));s['diagnostics']=inspect_failure(case)
 try:
  with lock(case):pass
 except RuntimeError:s['run_active']=True
 else:s['run_active']=False
 return s
