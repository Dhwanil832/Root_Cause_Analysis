import json
from shared.config_loader import ROOT,load_config
from orchestration.orchestrator import Investigator
from integrations.evidence_sources.synthetic_world import EvidenceWorld


def test_saved_model_inputs_never_include_unreleased_documents(tmp_path):
    a=Investigator(EvidenceWorld(ROOT/'evaluation/fixtures/wet_floor/documents.json'),
       load_config('config/experiments/v2_full.yaml'),mode='fixture',max_steps=1,
       fixture_responses=ROOT/'evaluation/private_reference/fixture_responses_DESIGNER_ONLY.json')
    a.run();a.output(tmp_path)
    items=json.loads((tmp_path/'model_inputs_MODEL_VISIBLE.json').read_text())
    assert items and len(items)==len(a.model_calls)
    first=json.dumps(items[:2])
    assert 'CAM-17' not in first and 'COR-17' not in first and 'WIT-06' not in first
    assert all(row['prompt_sha256']==a.registry.prompt_hashes[row['role']] for row in items)
    assert not any(row['actual_provider_completion'] for row in items)
    summary=json.loads((tmp_path/'summary.json').read_text())
    assert summary['provider_http_attempts']==0
