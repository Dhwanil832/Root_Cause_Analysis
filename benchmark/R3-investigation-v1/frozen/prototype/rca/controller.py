"""Atomic structural updates, supersession and source freshness; no RCA oracle."""
import copy,re,unicodedata
from .storage import event

def norm(x):return ' '.join(unicodedata.normalize('NFKC',x or '').casefold().split())
def fail(message):raise ValueError(message)
def active(item):return item['record']['status'] not in ['withdrawn','terminated'] and not item.get('superseded_by')
def apply(state,operations,actor):
 trial=copy.deepcopy(state);changes=[];noops=[]
 try:
  for op in operations:
   if set(op)!={'action','expected_version','replaces','reason','record'}:fail('operation_schema')
   r=op['record'];kind=r['kind'];rid=r['id'];action=op['action']
   required={'id','kind','scope_key','claim','status','sources','depends_on','from_ids','to_id','mode','asset','window','fields'}
   if set(r)!=required or kind not in ['node','edge','request']:fail('record_schema')
   if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,79}',rid):fail('invalid_id')
   if not all(isinstance(r[k],str) and r[k].strip() for k in ['scope_key','claim']):fail('missing_identity')
   if actor=='evidence' and kind!='request':fail('evidence_role_cannot_judge_physical_causes')
   if actor not in ['lead','intake','evidence']:fail('role_proposals_require_lead_review')
   for k in ['sources','depends_on','from_ids','fields']:
    if not isinstance(r[k],list) or any(not isinstance(x,str) for x in r[k]) or len(set(r[k]))!=len(r[k]):fail('invalid_list_'+k)
   if set(r['sources'])-set(state['sources']):fail('unknown_source')
   statuses={'node':['reported','candidate','supported','refuted','unresolved','conflicting','withdrawn'],'edge':['candidate','supported','refuted','unresolved','conflicting','withdrawn'],'request':['proposed','searching','awaiting_user','partial','answered','blocked','terminated']}
   if r['status'] not in statuses[kind]:fail('invalid_status_for_kind')
   if r['status'] in ['supported','refuted','conflicting','answered','blocked'] and not r['sources']:fail('judgment_needs_sources')
   if kind=='request':
    if not r['asset'] or not r['window'] or not r['fields']:fail('request_needs_scope_and_fields')
    if r['from_ids'] or r['to_id'] is not None or r['mode'] is not None:fail('request_not_physical_edge')
    if actor=='evidence' and r['status'] not in ['awaiting_user','partial','answered','blocked']:fail('evidence_role_status')
   elif r['asset'] is not None or r['window'] is not None or r['fields']:fail('physical_record_has_request_fields')
   if kind=='node' and (r['from_ids'] or r['to_id'] is not None or r['mode'] is not None):fail('node_has_edge_fields')
   if kind=='edge' and (not r['from_ids'] or not r['to_id'] or r['mode'] not in ['all','any'] or r['to_id'] in r['from_ids']):fail('invalid_edge')
   if type(op['expected_version']) is not int or not op['reason'].strip():fail('version_or_reason')
   old_id=op['replaces'] if action=='replace' else rid;old=trial['ledger'].get(old_id)
   if action=='create':
    if rid in trial['ledger'] or op['expected_version']!=0 or op['replaces'] is not None:fail('bad_create_identity_or_version')
   elif action in ['revise','replace']:
    if old is None or op['expected_version']!=old['version'] or not active(old):fail('unknown_stale_or_retired_revision')
    previous=old['record']
    if action=='revise':
     if op['replaces'] is not None:fail('revise_must_not_replace')
     if any(previous[k]!=r[k] for k in ['kind','scope_key','claim']):fail('identity_changed_use_replace')
     if kind=='edge' and (set(previous['from_ids'])!=set(r['from_ids']) or any(previous[k]!=r[k] for k in ['to_id','mode'])):fail('endpoints_or_mode_changed_use_replace')
     if kind=='request' and previous['asset']!=r['asset']:fail('asset_changed_use_replace')
     if r==previous and not old.get('stale'):
      noops.append(rid);continue
    else:
     if rid in trial['ledger'] or old_id==rid or previous['kind']!=kind:fail('replace_needs_new_id_same_kind')
     retired=copy.deepcopy(old);retired['superseded_by']=rid;retired['version']+=1;retired['record']['status']='terminated' if kind=='request' else 'withdrawn';retired['review']='superseded';trial['ledger'][old_id]=retired
     changes.append(dict(id=old_id,before=old,after=copy.deepcopy(retired),reason=op['reason']))
    if kind=='request' and previous['status'] in ['blocked'] and r['status'] in ['searching','awaiting_user','partial']:
     if set(r['sources'])<=set(previous['sources']):fail('blocked_route_needs_new_evidence')
   else:fail('unknown_action')
   for oid,other in trial['ledger'].items():
    if oid==rid or not active(other):continue
    o=other['record']
    if o['kind']!=kind:continue
    if norm(o['scope_key'])==norm(r['scope_key']):fail('duplicate_scope_reuse_'+oid)
    if kind=='node' and norm(o['claim'])==norm(r['claim']):fail('duplicate_claim_reuse_'+oid)
    if kind=='edge' and set(o['from_ids'])==set(r['from_ids']) and o['to_id']==r['to_id'] and o['mode']==r['mode']:fail('duplicate_edge_reuse_'+oid)
    if kind=='request' and r['status'] in ['proposed','searching','awaiting_user','partial'] and norm(o['asset'])==norm(r['asset']) and norm(o['window'])==norm(r['window']) and set(map(norm,o['fields']))&set(map(norm,r['fields'])):fail('overlapping_request_reuse_'+oid)
   ver=old['version']+1 if action=='revise' else 1
   item=dict(record=copy.deepcopy(r),version=ver,source_versions={s:state['sources'][s]['version'] for s in r['sources']},review='pending_human' if kind!='request' else 'not_applicable',stale=False)
   if action=='replace':item['supersedes']=old_id
   trial['ledger'][rid]=item;changes.append(dict(id=rid,before=copy.deepcopy(old) if action=='revise' else None,after=copy.deepcopy(item),reason=op['reason']))
  # Validate dependencies on the final transaction, permitting atomic dependent replacements.
  for rid,item in trial['ledger'].items():
   if not active(item):continue
   r=item['record'];deps=r['depends_on']+r['from_ids']+([r['to_id']] if r['to_id'] else [])
   if rid in deps:fail('self_dependency')
   for dep in deps:
    if dep not in trial['ledger'] or not active(trial['ledger'][dep]):fail('missing_or_retired_dependency_'+dep)
   if r['kind']=='edge' and any(trial['ledger'][d]['record']['kind']!='node' for d in r['from_ids']+[r['to_id']]):fail('nonphysical_endpoint')
  # Changed premises invalidate existing dependents unless explicitly reassessed in this batch.
  touched={c['id'] for c in changes};stale=set(touched)
  for _ in range(len(trial['ledger'])):
   grew=False
   for rid,item in trial['ledger'].items():
    r=item['record'];deps=set(r['depends_on']+r['from_ids']+([r['to_id']] if r['to_id'] else []))
    if rid not in touched and active(item) and deps&stale and rid not in stale:
     item['stale']=True;item['review']='pending_human' if r['kind']!='request' else 'not_applicable';stale.add(rid);grew=True
   if not grew:break
  trial['history'].extend(changes);event(trial,'controller_commit',actor=actor,operations=len(operations),changed_ids=sorted(touched))
  return trial,dict(accepted=True,operations=len(operations),changed=len(changes),noops=noops,reason=None)
 except (ValueError,KeyError,TypeError,AttributeError) as e:
  return state,dict(accepted=False,operations=len(operations),reason=str(e))
