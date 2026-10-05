"""A uniform strict schema; optional-kind fields are explicit nulls."""
from .contract import STATUSES, ContractError

def obj(props):return {'type':'object','properties':props,'required':list(props),'additionalProperties':False}
def arr(item):return {'type':'array','items':item}
def enum(*values):return {'type':'string','enum':list(values)}
S={'type':'string'};I={'type':'integer'};NS={'type':['string','null']}
RECORD=obj(dict(id=S,kind=enum('node','edge','request'),scope_key=S,claim=S,status=enum('reported','candidate','supported','refuted','unresolved','conflicting','withdrawn','proposed','searching','awaiting_user','partial','answered','blocked','terminated'),sources=arr(S),depends_on=arr(S),from_ids=arr(S),to_id=NS,mode={'type':['string','null'],'enum':['all','any',None]},asset=NS,window=NS,fields=arr(S)))
OP=obj(dict(action=enum('create','revise','replace'),expected_version=I,replaces=NS,reason=S,record=RECORD))
WORK=obj(dict(kind=enum('specialist','evidence','assessor'),tag=S,focus=S,target_ids=arr(S)))
UPSTREAM=obj(dict(target_id=S,action=enum('investigate','already_explained','blocked','out_of_scope','no_longer_applicable'),reason=S,record_ids=arr(S),source_ids=arr(S)))
OUTPUT=obj(dict(decision=S,operations=arr(OP),next_work=arr(WORK),upstream_dispositions=arr(UPSTREAM),disposition=enum('continue','waiting','partial')))

RECORD['properties']['id'] = dict(S, description='Fresh ledger ID on create/replace. Match [A-Za-z][A-Za-z0-9_-]{0,79}.')
RECORD['properties']['sources'] = dict(arr(S), description='Unique top-level source IDs, never section IDs. Put section/page locators in reason.')
RECORD['properties']['status'] = dict(RECORD['properties']['status'], description='Allowed by record kind: '+str(STATUSES))
OP['properties']['expected_version'] = dict(I, description='0 for create; current target ledger version for revise/replace.')
OP['properties']['reason'] = dict(S, description='Concrete evidence-grounded justification. Requests: per-field coverage, original source/locator, remaining gaps and reopening condition. Persisted with the record.')
OP['properties']['replaces'] = dict(NS, description='null for create/revise; old same-kind ledger ID for replace, which needs a fresh record.id.')

def validate(value,schema=OUTPUT,path='$'):
 """Identical schema checks on both transports, with localized repair details."""
 types=schema['type'];types=[types] if isinstance(types,str) else types
 actual={dict:'object',list:'array',str:'string',int:'integer',type(None):'null',bool:'boolean'}.get(type(value))
 def bad(code, **kw):
  raise ContractError(code,path=path,actual=value,repair='Return the required field value at this path; preserve other justified content.',**kw)
 if actual not in types:bad('schema_type',expected=types,actual_type=actual)
 if 'enum' in schema and value not in schema['enum']:bad('schema_enum',expected=schema['enum'])
 if actual=='object':
  missing=sorted(set(schema['required'])-set(value));extra=sorted(set(value)-set(schema['required']))
  if missing or extra:bad('schema_fields',expected=schema['required'],missing=missing,extra=extra)
  for k,v in value.items():validate(v,schema['properties'][k],path+'.'+k)
 elif actual=='array':
  for i,v in enumerate(value):validate(v,schema['items'],path+'['+str(i)+']')
