from pathlib import Path
import pytest
from shared.env_loader import load_env_file
from shared.config_loader import load_config,ROOT
from orchestration.orchestrator import Investigator
from integrations.evidence_sources.synthetic_world import EvidenceWorld


def test_local_env_file_loads_only_when_not_already_set(tmp_path,monkeypatch):
    monkeypatch.delenv('RCA_TEST_LOCAL_KEY',raising=False)
    p=tmp_path/'.env'
    p.write_text('RCA_TEST_LOCAL_KEY="local-value"\n# comment\ninvalid key=ignored\n')
    assert load_env_file(p)==1
    import os
    assert os.getenv('RCA_TEST_LOCAL_KEY')=='local-value'
    monkeypatch.setenv('RCA_TEST_LOCAL_KEY','environment-priority')
    assert load_env_file(p)==0
    assert os.getenv('RCA_TEST_LOCAL_KEY')=='environment-priority'


def test_unsupported_revision_fails_before_run():
    cfg=load_config();cfg['revision']['implementation']='v99-unimplemented'
    with pytest.raises(ValueError,match='v2 revision controller'):
        Investigator(EvidenceWorld(ROOT/'evaluation/fixtures/wet_floor/documents.json'),cfg)


def test_unsupported_orchestration_fails_before_run():
    cfg=load_config();cfg['orchestration']['mode']='fully_parallel'
    with pytest.raises(ValueError,match='sequential orchestration'):
        Investigator(EvidenceWorld(ROOT/'evaluation/fixtures/wet_floor/documents.json'),cfg)


def test_ablation_uses_only_one_enhanced_role():
    cfg=load_config('config/experiments/ablation_v2_frontier_only.yaml')
    active={k:v['implementation'] for k,v in cfg['agents'].items()}
    assert active=={
        'intake':'v1_basic','specialist':'v2_causal_frontier',
        'lead':'v1_basic','evidence_worker':'ablation_no_llm','assessor':'ablation_no_llm'}
