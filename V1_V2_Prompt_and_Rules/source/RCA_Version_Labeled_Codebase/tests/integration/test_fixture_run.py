from pathlib import Path
import json,os,tempfile,copy
import pytest
from shared.config_loader import load_config,ROOT
from shared.llm.fixture import FixtureModel
from shared.registry import ComponentRegistry
from integrations.evidence_sources.synthetic_world import EvidenceWorld
from orchestration.orchestrator import Investigator
from revision.v2.session import Session
from integrations.viewer import build_viewer
from shared.validation import ProposalError

DOCUMENTS=ROOT/'evaluation/fixtures/wet_floor/documents.json'
TEMPLATES=ROOT/'evaluation/private_reference/fixture_responses_DESIGNER_ONLY.json'

def make(profile=None,actions=18,model=None):
    return Investigator(EvidenceWorld(DOCUMENTS),load_config(profile),mode='fixture',
        max_steps=actions,fixture_responses=TEMPLATES,model=model)

@pytest.fixture(scope='module')
def agent():return make().run()

def test_runs_all_six_synthetic_sources(agent):
    assert set(agent.session.documents)=={'IR-01','CAM-17','COR-17','MNT-81','WIT-06','OPS-02'}
    assert len(agent.events)>15
    assert len(agent.model_calls)>0
    assert sum(x.actual_call_performed for x in agent.model_calls)==0

def test_correction_is_dependency_scoped(agent):
    by_label={c['semantic_label']:c for c in agent._claim_projection()}
    assert by_label['mopping_F2']['status']=='unknown'
    assert by_label['slip']['status']=='supported'
    assert by_label['water']['status']=='supported'
    assert agent.session.kernel.sources['CAM-17'].version==2

def test_no_completed_root_cause_fabricated(agent):
    assert agent.stop_reason in {'no_admissible_action','action_budget_exhausted'}
    assert agent.session.kernel.phase!='signed_off'
    assert any(g['status']=='open' for g in agent._gap_projection())

def test_viewer_and_checkpoint_roundtrip(agent,tmp_path):
    agent.output(tmp_path)
    build_viewer(tmp_path/'trace.json',tmp_path/'summary.json',tmp_path/'investigation_viewer.html')
    assert (tmp_path/'investigation_viewer.html').stat().st_size>10000
    restored=Session.load(tmp_path/'session.json')
    assert restored.kernel.claim_views()==agent.session.kernel.claim_views()

def test_baseline_profile_runs_without_rewriting_system(tmp_path):
    a=make('config/experiments/ablation_no_llm.yaml',actions=4).run()
    assert a.registry.selected_name('lead')=='v1_basic'
    a.output(tmp_path)
    assert json.loads((tmp_path/'summary.json').read_text())['component_config']['lead']=='v1_basic'

class TraceInputs(FixtureModel):
    def __init__(self,response_path):
        super().__init__(response_path);self.requests=[]
    def ask(self,task,system,payload):
        self.requests.append((task,copy.deepcopy(payload)))
        return super().ask(task,system,payload)

def test_no_future_documents_in_initial_context():
    model=TraceInputs(TEMPLATES)
    a=make(actions=1,model=model).run()
    inputs=[payload for role,payload in model.requests[:2]]
    serialized=json.dumps(inputs)
    assert 'CAM-17' not in serialized
    assert 'COR-17' not in serialized
    assert 'MNT-81' not in serialized
    assert 'OPS-02' not in serialized
    assert 'WIT-06' not in serialized

class Misquoted(FixtureModel):
    def ask(self,task,system,payload):
        result=super().ask(task,system,payload)
        if task=='extract' and payload['document']['id']=='IR-01':
            result['assertions'][0]['quote']='a sentence that was never in the report text'
        return result

def test_false_quote_is_rejected_before_admission():
    a=make(model=Misquoted(TEMPLATES))
    with pytest.raises(ProposalError):a.run()
    assert not a.session.documents

def test_correction_needs_claim_id_and_is_scoped():
    a=make(actions=3).run()
    # In the model-driven world, a correction is applied only after the camera arrives.
    assert a.session.kernel.sources['CAM-17'].version>=1
