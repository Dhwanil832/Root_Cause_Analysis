from pathlib import Path
from types import SimpleNamespace
from reasoning.lead.implementations import v1_basic as baseline, v2_causal_guided as causal_guided, v2_joint_route_planner as joint_route_planner
from reasoning.specialist.implementations import v1_basic as simple_frontier
from reasoning.specialist.implementations import v2_causal_frontier as causal_frontier

class FakeRuntime:
    def __init__(self):
        self.gaps={'c':{'kind':'causal','status':'open'}, 'o':{'kind':'operational','status':'open'}}
        self.attempts=[];self.discoveries=[];self.hypotheses={'a':'h1','b':'h2'}

def act(gid,mode,route,directness=1,burden=1):
    return dict(gap_id=gid,mode=mode,route=route,question='Please provide source details',
        information_needed='Equipment operations near incident', possible_effect='Distinguish alternative accident mechanisms',
        directness=directness,burden=burden)

def test_swaps_share_action_contract_but_different_policy():
    runtime=FakeRuntime()
    public={'routes':[{'id':'maintenance'}]}
    options=[act('o','request','maintenance',directness=1),act('c','discover','security',directness=3)]
    b=baseline.rank(runtime,options,public)
    j=joint_route_planner.rank(runtime,options,public)
    assert b[0]['action']['route']=='maintenance'
    assert j[0]['action']['route']=='security'
    assert all('score' in item and 'action' in item for item in b+j)

def test_unknown_route_must_be_discovered():
    runtime=FakeRuntime()
    public={'routes':[]}
    assert joint_route_planner.rank(runtime,[act('c','request','security')],public)==[]
    assert joint_route_planner.rank(runtime,[act('c','discover','security')],public)

def test_no_repeat_request_to_same_route():
    runtime=FakeRuntime()
    runtime.attempts=[{'gap_id':'c','route':'maintenance','mode':'request'}]
    public={'routes':[{'id':'maintenance'}]}
    assert not joint_route_planner.rank(runtime,[act('c','request','maintenance')],public)

def test_frontier_deduplicates_same_question_without_inventing_cause():
    raw={'new_gaps':[{'question':'Why did it slip?','semantic_label':'A'},{'question':'Why did it slip?','semantic_label':'B'}],
         'hypotheses':[{'summary':'Leak'},{'summary':'Leak'}]}
    out=causal_frontier.transform(raw,{'gaps':[]})
    assert len(out['new_gaps'])==1
    assert len(out['hypotheses'])==1
    assert len(simple_frontier.transform(raw,{} )['new_gaps'])==2
