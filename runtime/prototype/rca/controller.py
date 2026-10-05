"""Atomic structural updates, supersession and source freshness; no RCA oracle."""
import copy,re,unicodedata
from .storage import event
from . import schema,freshness
from .contract import ID_PATTERN, STATUSES, SOURCE_REQUIRED, UNIQUE_LISTS, ContractError

def norm(x):return ' '.join(unicodedata.normalize('NFKC',x or '').casefold().split())
def active(item):return item['record']['status'] not in ['withdrawn','terminated'] and not item.get('superseded_by')
def apply(state,operations,actor):
 trial=copy.deepcopy(state);changes=[];noops=[];index=None;rid=None;r={};op={}
 def fail(code,field=None,expected=None,repair=None,**extra):
  path=f'$.operations[{index}]' if index is not None else '$.ledger'
  if field:path+='.'+field
  actual=op
  if field:
   for part in field.split('.'):
    actual=actual.get(part) if isinstance(actual,dict) else None
  raise ContractError(code,phase='controller',operation_index=index,record_id=rid,path=path,actual=actual,
      expected=expected if expected is not None else 'A record satisfying the mechanical update contract',
      repair=repair or 'Correct the identified record using current ledger/source versions and the mechanical contract; resubmit the whole justified batch.',**extra)
 try:
  for index,op in enumerate(operations):
   rid=op.get('record',{}).get('id') if isinstance(op,dict) else None
   schema.validate(op,schema.OP,f'$.operations[{index}]')
   if set(op)!={'action','expected_version','replaces','reason','record'}:fail('operation_schema')
   r=op['record'];kind=r['kind'];rid=r['id'];action=op['action']
   required={'id','kind','scope_key','claim','status','sources','depends_on','from_ids','to_id','mode','asset','window','fields'}
   if set(r)!=required or kind not in ['node','edge','request']:fail('record_schema')
   if not re.fullmatch(ID_PATTERN,rid):fail('invalid_id','record.id',ID_PATTERN)
   if not all(isinstance(r[k],str) and r[k].strip() for k in ['scope_key','claim']):fail('missing_identity','record', 'Nonblank claim and scope_key')
   if actor=='evidence' and kind!='request':fail('evidence_role_cannot_judge_physical_causes')
   if actor not in ['lead','intake','evidence']:fail('role_proposals_require_lead_review')
   for k in UNIQUE_LISTS:
    if not isinstance(r[k],list) or any(not isinstance(x,str) for x in r[k]) or len(set(r[k]))!=len(r[k]):fail('invalid_list_'+k,'record.'+k,'Unique strings')
   if set(r['sources'])-set(state['sources']):fail('unknown_source','record.sources',sorted(state['sources']),'Use supplied top-level source IDs; put section/page locators in reason.',unknown_ids=sorted(set(r['sources'])-set(state['sources'])))
   if r['status'] not in STATUSES[kind]:fail('invalid_status_for_kind','record.status',STATUSES[kind])
   if r['status'] in SOURCE_REQUIRED and not r['sources']:fail('judgment_needs_sources','record.sources','At least one supplied source ID with evidence for this status; otherwise preserve uncertainty')
   if kind=='request':
    if not r['asset'] or not r['window'] or not r['fields']:fail('request_needs_scope_and_fields','record','Nonempty asset, window and fields')
    if r['from_ids'] or r['to_id'] is not None or r['mode'] is not None:fail('request_not_physical_edge','record',dict(from_ids=[],to_id=None,mode=None))
    if actor=='evidence' and r['status'] not in ['awaiting_user','partial','answered','blocked']:fail('evidence_role_status','record.status',['awaiting_user','partial','answered','blocked'])
   elif r['asset'] is not None or r['window'] is not None or r['fields']:fail('physical_record_has_request_fields','record',dict(asset=None,window=None,fields=[]))
   if kind=='node' and (r['from_ids'] or r['to_id'] is not None or r['mode'] is not None):fail('node_has_edge_fields','record',dict(from_ids=[],to_id=None,mode=None))
   if kind=='edge' and (not r['from_ids'] or not r['to_id'] or r['mode'] not in ['all','any'] or r['to_id'] in r['from_ids']):fail('invalid_edge','record','Nonempty node endpoints, mode all/any, target not among premises')
   if type(op['expected_version']) is not int or not op['reason'].strip():fail('version_or_reason',None,'Integer expected_version and nonblank reason')
   old_id=op['replaces'] if action=='replace' else rid;old=trial['ledger'].get(old_id)
   if action=='create':
    if rid in trial['ledger'] or op['expected_version']!=0 or op['replaces'] is not None:fail('bad_create_identity_or_version',None,dict(id='fresh ledger ID',expected_version=0,replaces=None))
   elif action in ['revise','replace']:
    if old is None:fail('unknown_revision_target','replaces' if action=='replace' else 'record.id',sorted(trial['ledger']))
    if op['expected_version']!=old['version']:fail('version_mismatch','expected_version',old['version'],target_id=old_id)
    if not active(old):fail('retired_revision_target','record.id','Active record',target_id=old_id,superseded_by=old.get('superseded_by'))
    previous=old['record']
    if action=='revise':
     if op['replaces'] is not None:fail('revise_must_not_replace','replaces','null')
     if any(previous[k]!=r[k] for k in ['kind','scope_key','claim']):fail('identity_changed_use_replace','record',{k:previous[k] for k in ['kind','scope_key','claim']},'Keep identity verbatim or replace with a fresh same-kind ID.')
     if kind=='edge' and (set(previous['from_ids'])!=set(r['from_ids']) or any(previous[k]!=r[k] for k in ['to_id','mode'])):fail('endpoints_or_mode_changed_use_replace','record',{k:previous[k] for k in ['from_ids','to_id','mode']},'Use replace with a new edge ID for changed endpoint membership/mode.')
     if kind=='request' and previous['asset']!=r['asset']:fail('asset_changed_use_replace','record.asset',previous['asset'],'Replace the request with a fresh ID when its asset changes.')
     if r==previous and not old.get('stale'):
      noops.append(rid);continue
    else:
     if rid in trial['ledger'] or old_id==rid or previous['kind']!=kind:fail('replace_needs_new_id_same_kind','record',dict(id='fresh ledger ID',kind=previous['kind']),existing_id=rid in trial['ledger'],replaced_id=old_id)
     retired=copy.deepcopy(old);retired['superseded_by']=rid;retired['version']+=1;retired['record']['status']='terminated' if kind=='request' else 'withdrawn';retired['review']='superseded';trial['ledger'][old_id]=retired
     changes.append(dict(id=old_id,before=old,after=copy.deepcopy(retired),reason=op['reason']))
    if kind=='request' and previous['status'] in ['blocked'] and r['status'] in ['searching','awaiting_user','partial']:
     fresh=[sid for sid in r['sources'] if sid not in previous['sources'] or state['sources'][sid]['version']>old.get('source_versions',{}).get(sid,state['sources'][sid]['version'])]
     if not fresh:fail('blocked_route_needs_new_evidence','record.sources','New cited source ID or newer cited source version','Preserve blocked unless evidence opens a real new route; cite that evidence and explain it.',previous_source_versions=old.get('source_versions',{}))
   else:fail('unknown_action')
   for oid,other in trial['ledger'].items():
    if oid==rid or not active(other):continue
    o=other['record']
    if o['kind']!=kind:continue
    if norm(o['scope_key'])==norm(r['scope_key']):fail('duplicate_scope_reuse_'+oid,'record.scope_key','Unique normalized scope within kind','Reuse the matched record or define a genuinely distinct scope.',matched_record_id=oid,matched_status=o['status'])
    if kind=='node' and norm(o['claim'])==norm(r['claim']):fail('duplicate_claim_reuse_'+oid,'record.claim','Distinct normalized node claim','Reuse the existing node.',matched_record_id=oid)
    if kind=='edge' and set(o['from_ids'])==set(r['from_ids']) and o['to_id']==r['to_id'] and o['mode']==r['mode']:fail('duplicate_edge_reuse_'+oid,'record','Distinct endpoint set/mode','Reuse or revise the existing edge.',matched_record_id=oid)
    if kind=='request' and r['status'] in ['proposed','searching','awaiting_user','partial'] and norm(o['asset'])==norm(r['asset']) and norm(o['window'])==norm(r['window']) and set(map(norm,o['fields']))&set(map(norm,r['fields'])):fail('overlapping_request_reuse_'+oid,'record.fields','No overlapping field for the same normalized asset/window','Reuse the matched acquisition or request only distinct uncovered fields; do not reopen a known boundary without evidence.',matched_record_id=oid,matched_status=o['status'],overlapping_fields=sorted(set(map(norm,o['fields']))&set(map(norm,r['fields']))))
   ver=old['version']+1 if action=='revise' else 1
   item=dict(record=copy.deepcopy(r),version=ver,source_versions={s:state['sources'][s]['version'] for s in r['sources']},review='pending_human' if kind!='request' else 'not_applicable',stale=False)
   item['justification']=dict(reason=op['reason'],actor=actor,version=ver,source_versions=item['source_versions'])
   if old and old.get('human_review'):item['human_review']=copy.deepcopy(old['human_review'])
   if kind=='request':
    # Coverage carries exact model explanations and scope transitions, never inferred answers.
    coverage=copy.deepcopy((old or {}).get('coverage',[]))
    before_fields=(old or {}).get('record',{}).get('fields',[])
    entry=dict(version=ver,status=r['status'],fields=copy.deepcopy(r['fields']),removed_fields=[f for f in before_fields if f not in r['fields']],reason=op['reason'],sources=copy.deepcopy(r['sources']),source_versions=item['source_versions'])
    coverage.append(entry);item['coverage']=coverage
   if action=='replace':item['supersedes']=old_id
   trial['ledger'][rid]=item;changes.append(dict(id=rid,before=copy.deepcopy(old) if action=='revise' else None,after=copy.deepcopy(item),reason=op['reason']))
  # Validate dependencies on the final transaction, permitting atomic dependent replacements.
  for rid,item in trial['ledger'].items():
   index=next((i for i,x in enumerate(operations) if x['record']['id']==rid),None)
   op=operations[index] if index is not None else {'record':item['record']}
   if not active(item):continue
   r=item['record'];deps=r['depends_on']+r['from_ids']+([r['to_id']] if r['to_id'] else [])
   if rid in deps:fail('self_dependency','record.depends_on','Other active ledger records')
   for dep in deps:
    if dep not in trial['ledger'] or not active(trial['ledger'][dep]):fail('missing_or_retired_dependency_'+dep,'record','All dependencies active in final batch','Update or retire all active dependents when replacing their target.',dependency_id=dep)
   if r['kind']=='edge' and any(trial['ledger'][d]['record']['kind']!='node' for d in r['from_ids']+[r['to_id']]):fail('nonphysical_endpoint','record','All from_ids/to_id endpoints must be node records')
  # A request is acquisition bookkeeping, not a physical proof premise. Reaffirming
  # an unchanged stale judgment also must not start a new invalidation wave.
  touched={c['id'] for c in changes}
  material={rid for rid in touched if trial['ledger'][rid]['record']['kind']!='request'
            and (rid not in state['ledger'] or freshness.meaning(state['ledger'],state['ledger'][rid])!=freshness.meaning(trial['ledger'],trial['ledger'][rid]))}
  # A same-content dependent explicitly reviewed in this batch is not a noop
  # when another operation changes its proof. Persist that reassessment and
  # revoke old approval, rather than discarding it and immediately staling it.
  affected=set(freshness.invalidate(copy.deepcopy(trial),material,{},protected=touched))
  for rid in set(noops)&affected:
   assessment=next(x for x in reversed(operations) if x['record']['id']==rid)
   old=copy.deepcopy(trial['ledger'][rid]);item=trial['ledger'][rid]
   item['version']+=1;item['stale']=False;item.pop('stale_causes',None)
   item['review']='pending_human'
   item['justification']=dict(reason=assessment['reason'],actor=actor,version=item['version'],source_versions=item['source_versions'])
   changes.append(dict(id=rid,before=old,after=copy.deepcopy(item),reason=assessment['reason']))
   touched.add(rid);noops.remove(rid)
  invalidated=freshness.invalidate(trial,material,dict(kind='judgment_changed',record_ids=sorted(material)),protected=touched)
  trial['history'].extend(changes);event(trial,'controller_commit',actor=actor,operations=len(operations),changed_ids=sorted(touched),material_change_ids=sorted(material),invalidated_ids=invalidated)
  return trial,dict(accepted=True,operations=len(operations),changed=len(changes),noops=noops,reason=None,invalidated_ids=invalidated)
 except (ValueError,KeyError,TypeError,AttributeError) as e:
  detail=getattr(e,'detail',dict(code='invalid_operation',path=f'$.operations[{index}]',record_id=rid,detail=str(e),repair='Supply a valid operation under the contract.'))
  return state,dict(accepted=False,operations=len(operations),reason=str(e),operations_accepted=False,committed=False,errors=[detail],validation_scope='First blocking error; later dependent operations have not been validated.',repair='No operations committed. Correct the identified error and resubmit a justified atomic batch.')
