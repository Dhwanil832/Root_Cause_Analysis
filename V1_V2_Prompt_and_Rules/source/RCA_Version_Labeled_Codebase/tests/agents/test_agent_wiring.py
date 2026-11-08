from pathlib import Path
from shared.config_loader import load_config,ROOT
from integrations.evidence_sources.synthetic_world import EvidenceWorld
from orchestration.orchestrator import Investigator
from shared.llm.fixture import FixtureModel

DOC=ROOT/'evaluation/fixtures/wet_floor/documents.json'
RESP=ROOT/'evaluation/private_reference/fixture_responses_DESIGNER_ONLY.json'


def run(profile):
    a=Investigator(EvidenceWorld(DOC),load_config(profile),mode='fixture',
                   max_steps=8,fixture_responses=RESP)
    a.run()
    return a


def test_full_system_calls_all_five_role_interfaces_not_only_intake_lead_specialist():
    a=run('config/experiments/v2_full.yaml')
    tasks=[c.task for c in a.model_calls]
    assert all(task in tasks for task in ('extract','frontier','propose_actions','plan_route','review_assessment'))
    assert a.assessment_history and a.assessment_history[0]['model_review_performed']
    assert a.routing_history
    assert all(not c.actual_call_performed for c in a.model_calls)  # fixture, NOT real LLM


def test_baseline_ablation_truly_omits_second_stage_calls():
    a=run('config/experiments/ablation_no_llm.yaml')
    tasks=[c.task for c in a.model_calls]
    assert 'review_assessment' not in tasks
    assert 'plan_route' not in tasks
    assert all(not r['model_review_performed'] for r in a.assessment_history)


def test_assessor_quarantine_changes_committed_evidence_not_just_trace():
    """Same bogus Intake output: baseline keeps it, enhanced review removes it."""
    from shared.validation import ProposalError

    class InjectUnsupportedIncidentFact(FixtureModel):
        def ask(self,task,system,payload):
            result=super().ask(task,system,payload)
            if task=='extract' and payload['document']['id']=='IR-01':
                result['assertions'].append({
                    'semantic_label':'invented_incident_leak','subject':'F2',
                    'predicate':'incident_time_leak_proven','scope':'at_10_05',
                    'configuration':'reported','polarity':True,
                    'basis':'assessed_source_assertion',
                    'quote':'The source of the water was unknown when this report was filed.',
                })
            if task=='review_assessment' and payload['document']['id']=='IR-01':
                result={'exclude_assertion_labels':['invented_incident_leak'],
                        'exclude_inference_indices':[], 'exclude_hypothesis_summaries':[],
                        'flags':[{'kind':'entailment','quote':'The source of the water was unknown when this report was filed.',
                                  'reason':'This quote contradicts the claimed certainty of an incident-time leak'}],
                        'reason':'Quarantine unsupported incident observation'}
            return result

    model=InjectUnsupportedIncidentFact(RESP)
    config=load_config('config/experiments/v2_full.yaml')
    enhanced=Investigator(EvidenceWorld(DOC),config,mode='fixture',model=model,max_steps=1)
    enhanced.run()
    assert 'invented_incident_leak' not in {c['semantic_label'] for c in enhanced._claim_projection()}
    assert enhanced.assessment_history[0]['excluded_assertion_labels']==['invented_incident_leak']
    assert 'The source of the water was unknown' in enhanced.session.documents['IR-01']['text']  # raw document retained

    base=Investigator(EvidenceWorld(DOC),load_config('config/experiments/ablation_no_llm.yaml'),
                      mode='fixture',model=InjectUnsupportedIncidentFact(RESP),max_steps=1)
    base.run()
    assert 'invented_incident_leak' in {c['semantic_label'] for c in base._claim_projection()}
    assert base.assessment_history[0]['model_review_performed'] is False


def test_evidence_worker_can_redirect_without_access_to_private_inventory():
    class Redirect(FixtureModel):
        def ask(self,task,system,payload):
            result=super().ask(task,system,payload)
            if task=='plan_route' and payload['proposed_action']['route']=='security':
                result={**result,'decision':'redirect','route':'maintenance',
                        'reason':'A maintenance route is already proposed for this same information need'}
            return result
    cfg=load_config('config/experiments/ablation_no_llm.yaml')
    cfg['agents']['evidence_worker']['implementation']='v2_adaptive_routes'
    a=Investigator(EvidenceWorld(DOC),cfg,
                   mode='fixture',model=Redirect(RESP),max_steps=2)
    a.run()
    assert any(x.get('changed_route') and x.get('selected_route')=='maintenance'
               for x in a.routing_history)
    assert 'CAM-17' not in a.session.documents  # not silently unlocked
    assert any(x.get('route')=='maintenance' for x in a.discoveries)
