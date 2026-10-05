"""A uniform strict schema; optional-kind fields are explicit nulls."""
def obj(props):return {'type':'object','properties':props,'required':list(props),'additionalProperties':False}
def arr(item):return {'type':'array','items':item}
def enum(*values):return {'type':'string','enum':list(values)}
S={'type':'string'};I={'type':'integer'};NS={'type':['string','null']}
RECORD=obj(dict(id=S,kind=enum('node','edge','request'),scope_key=S,claim=S,status=enum('reported','candidate','supported','refuted','unresolved','conflicting','withdrawn','proposed','searching','awaiting_user','partial','answered','blocked','terminated'),sources=arr(S),depends_on=arr(S),from_ids=arr(S),to_id=NS,mode={'type':['string','null'],'enum':['all','any',None]},asset=NS,window=NS,fields=arr(S)))
OP=obj(dict(action=enum('create','revise','replace'),expected_version=I,replaces=NS,reason=S,record=RECORD))
WORK=obj(dict(kind=enum('specialist','evidence','assessor'),tag=S,focus=S,target_ids=arr(S)))
OUTPUT=obj(dict(decision=S,operations=arr(OP),next_work=arr(WORK),disposition=enum('continue','waiting','partial')))
