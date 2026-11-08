"""Distinct behavior, counterexamples, and monotonic properties of V2 modules."""
from copy import deepcopy
from types import SimpleNamespace
from pathlib import Path
from reasoning.specialist.components.hypothesis_matrix import compile_matrix
from reasoning.lead.components.coverage_selection import rank_one_step
from reasoning.lead.components.priority_scoring import score_action
from reasoning.evidence_worker.components.route_map import inspect_routes
from reasoning.assessor.components.scope_guard import inspect_scope_risks
from reasoning.assessor.implementations.v2_impact_aware import review
from shared.config_loader import ROOT


def hypothetical():
    # Research fixture does not encode the real R3 or wet-floor gold causal path.
    return [{'summary':'A belt jam might cause the package drop',
             'missing_conditions':['The belt stopped before the package fell'],
             'tests':['Time-aligned belt motion record']},
            {'summary':'An operator release might cause the package drop',
             'missing_conditions':['An operator released the package before it fell'],
             'tests':['Firsthand operator release observation']}]


def gap(label, text, route):
    return {'id':label,'semantic_label':label,'kind':'causal','status':'open',
            'question':text,'expected_change':'Distinguish proposed package-drop mechanisms',
            'routes_to_consider':[{'route':route,'topic':text,'directness':2,'burden':1}]}


def action(gid,route,mode='request',burden=1):
    return {'mode':mode,'gap_id':gid,'route':route,'directness':2,'burden':burden,
            'question':'Please obtain the event-time source observation',
            'information_needed':'Time-scoped package movement observations',
            'possible_effect':'Distinguishes package-drop explanations'}


def test_hypothesis_matrix_exposes_unquestioned_conditions_not_causes():
    cases=hypothetical()
    gaps=[gap('g1','Did the belt stop before the package fell?','controls')]
    result=compile_matrix(cases,gaps)
    assert result['missing_condition_count']==2
    assert result['unquestioned_conditions']==[{'hypothesis':cases[1]['summary'],
       'missing_condition':cases[1]['missing_conditions'][0]}]
    assert gaps[0]['hypothesis_tests']==[cases[0]['summary']]
    assert gaps[0]['discrimination_class']=='mechanism_specific'
    assert 'established' not in str(result)


def test_lead_coverage_method_values_shared_route_without_future_answer_oracle():
    g=[gap('g1','Did the belt stop before the package fell?','controls'),
       gap('g2','What do the motor encoder records show?','controls'),
       gap('g3','Was the belt alarm triggered?','controls')]
    r=SimpleNamespace(gaps={x['id']:x for x in g},attempts=[],discoveries=[])
    public={'gaps':g,'routes':[],'hypotheses':hypothetical(),'graph_frontier':{}}
    a=action('g1','controls','discover')
    choice=rank_one_step(r,[a],public,score_action)[0]
    assert choice['breakdown']['open_needs_accessible_via_route']==3
    assert choice['breakdown']['route_access']>2
    assert choice['breakdown']['method'] if 'method' in choice['breakdown'] else True
    assert choice['breakdown']['score_type']=='ordinal_heuristic_not_expected_information_gain'
    assert 'prediction' not in str(choice)
    fewer={**public,'gaps':[g[0]]}
    short=rank_one_step(r,[a],fewer,score_action)[0]
    assert choice['score']>short['score']


def test_lead_cost_penalty_and_retry_guard_are_effective():
    g=[gap('g1','Did the belt stop before the package fell?','controls')]
    r=SimpleNamespace(gaps={'g1':g[0]},attempts=[],discoveries=[])
    public={'gaps':g,'routes':[{'id':'controls'}], 'hypotheses':[], 'graph_frontier':{}}
    low=rank_one_step(r,[action('g1','controls',burden=0)],public,score_action)[0]['score']
    high=rank_one_step(r,[action('g1','controls',burden=4)],public,score_action)[0]['score']
    assert low > high
    r.attempts.append({'gap_id':'g1','route':'controls','mode':'request'})
    assert rank_one_step(r,[action('g1','controls')],public,score_action)==[]


def test_route_map_excludes_exhausted_route_and_never_adds_private_file_ids():
    g=gap('g1','Did the belt stop before the package fell?','controls')
    public={'gaps':[g], 'routes':[{'id':'controls','description':'Belt controller logs'}],
            'attempts':[]}
    candidates=inspect_routes(g,public)
    assert candidates[0]['route']=='controls' and candidates[0]['mode']=='request'
    assert 'doc_id' not in str(candidates) and 'hidden' not in str(candidates)
    public['attempts']=[{'gap_id':'g1','route':'controls','status':'partial'}]
    assert inspect_routes(g,public)==[]


def test_assessor_scope_guard_flags_incident_time_bench_test_and_not_generic_warrant():
    source={'id':'S','text':'The post-event bench test showed 10 mL of leakage.'}
    bad=[{'semantic_label':'instant_leak','basis':'documented_measurement',
          'scope':'incident_window','configuration':'incident',
          'predicate':'incident_flow_measurement','quote':source['text']}]
    risk=inspect_scope_risks(source,bad,{'inferences':[]})
    assert risk['quarantine_assertion_labels']==['instant_leak']
    general=[{'semantic_label':'generic_warrant','basis':'conditional_model',
              'scope':'normal_operation','configuration':'general',
              'predicate':'can_leak_if_worn','quote':'A worn seal may permit leakage.'}]
    assert not inspect_scope_risks(source,general,{})['quarantine_assertion_labels']


def test_assessor_scope_quarantine_keeps_unrelated_claim_and_open_gap():
    source={'id':'S','text':'A later bench test was performed. The operator reported the package jam.'}
    claims=[{'semantic_label':'instant_reading','basis':'documented_measurement',
             'scope':'incident_time','configuration':'incident',
             'predicate':'incident_hydraulic_reading','quote':'A later bench test was performed.'},
            {'semantic_label':'jam_report','basis':'assessed_source_assertion',
             'scope':'incident_time','configuration':'reported',
             'predicate':'reported_package_jam','quote':'The operator reported the package jam.'}]
    frontier={'hypotheses':[], 'inferences':[], 'resolved_gaps':[
        {'gap_id':'G1','supporting_assertion_labels':['instant_reading']},
        {'gap_id':'G2','supporting_assertion_labels':['jam_report']} ]}
    class FakeRuntime:
        def ask_role(self,role,task,payload):
            assert payload['deterministic_scope_review']['quarantine_assertion_labels']==['instant_reading']
            return {'exclude_inference_indices':[], 'exclude_hypothesis_summaries':[],
                    'exclude_assertion_labels':[], 'flags':[], 'reason':'No additional model findings'}
    out=review(FakeRuntime(),source,{'existing_claims':[],'hypotheses':[],'gaps':[]},
               {},frontier,claims)
    assert [x['semantic_label'] for x in out['new_claims']]==['jam_report']
    assert out['assessment']['suppressed_gap_resolutions']==['G1']
    assert out['frontier']['resolved_gaps']==[frontier['resolved_gaps'][1]]
    assert 'instant_reading' in out['assessment']['scope_guard_quarantined']
