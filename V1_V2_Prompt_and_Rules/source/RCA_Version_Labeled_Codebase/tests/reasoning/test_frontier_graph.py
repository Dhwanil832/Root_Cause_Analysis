"""Structured frontier never asserts causes on its own."""
from revision.v2.session import Session
from revision.v2.kernel import Key,Source,Observation
from reasoning.specialist.components.frontier_graph import inspect_frontier

def test_empty_frontier_no_hypotheses_invented():
    r=inspect_frontier(Session())
    assert r['unresolved_link_premises']==[]
    assert r['supported_source_assertions']==[]

def test_frontier_has_stated_sources_but_no_assumed_causes():
    s=Session()
    k=Key('worker','slipped','10:05','incident')
    s.kernel.receive(Source('IR',1,'report',(Observation(k),)))
    r=inspect_frontier(s)
    assert any(x['key']==k.label() for x in r['supported_source_assertions'])
    assert r['unresolved_link_premises']==[]

def test_missing_condition_is_not_automatically_supported():
    s=Session()
    cause=Key('machine','hose_leak','incident','incident')
    effect=Key('floor','wet','incident','incident')
    s.mechanisms['M']={'id':'M','causes':[cause.label()],'effect':effect.label(),
                       'grade':'hypothesis','rationale':'candidate only'}
    result=inspect_frontier(s)
    assert cause.label() in result['unresolved_link_premises'][0]['missing_premises']
    assert s.kernel.status(cause)=='unknown'
