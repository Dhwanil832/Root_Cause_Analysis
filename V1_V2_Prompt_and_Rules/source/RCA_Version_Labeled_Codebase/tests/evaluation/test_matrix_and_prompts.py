"""Fair prompt/method ablation wiring and evaluator integrity checks."""
from pathlib import Path
import json
from shared.config_loader import ROOT,load_config
from shared.registry import ComponentRegistry
from evaluation.run_matrix import run_matrix
from evaluation.metrics.behavioral import inspect_run
from evaluation.metrics.reviewer_sheet import COLUMNS


def test_full_v2_agent_prompts_are_distinct_and_materially_detailed():
    cfg=load_config('config/experiments/v2_full.yaml')
    registry=ComponentRegistry(cfg)
    for role in registry.components:
        prompt=registry.prompt(role)
        assert len(prompt.split()) > 240, (role,len(prompt.split()))
        assert 'JSON' in prompt.upper()
        assert 'source' in prompt.lower() or 'document' in prompt.lower()
        assert 'not' in prompt.lower() or 'never' in prompt.lower()
    assert len(set(registry.prompt_hashes.values()))==5
    baselines=ComponentRegistry(load_config('config/experiments/v1_basic.yaml'))
    assert any(registry.prompt_hashes[r]!=baselines.prompt_hashes[r]
               for r in registry.components)


def test_prompt_switch_does_not_change_component_code_or_model_calls_spec():
    baseline=ComponentRegistry(load_config('config/experiments/v1_basic.yaml'))
    better=ComponentRegistry(load_config('config/experiments/v2_prompts_only.yaml'))
    for role in baseline.components:
        assert baseline.selected_name(role)==better.selected_name(role)
        assert baseline.prompt_hashes[role]!=better.prompt_hashes[role]
    methods=ComponentRegistry(load_config('config/experiments/v2_methods_only.yaml'))
    full=ComponentRegistry(load_config('config/experiments/v2_full.yaml'))
    for role in methods.components:
        assert methods.selected_name(role)==full.selected_name(role)
        assert methods.prompt_hashes[role]!=full.prompt_hashes[role]


def test_factorial_matrix_uses_isolated_fixture_worlds(tmp_path):
    output=run_matrix(tmp_path,mode='fixture',max_actions=18)
    assert set(x['profile'] for x in output['profiles']) == {
        'v1_prompt_only','v2_prompts_only','v2_methods_only','v2_full'}
    assert all(r['run_status']=='completed' for r in output['profiles'])
    assert all(r['provider_http_completions']==0 for r in output['profiles'])
    assert all(all(r['authored_fixture_invariants'].values()) for r in output['profiles'])
    assert output['independent_model_validation'] is False
    a=inspect_run(tmp_path/'v1_prompt_only')
    b=inspect_run(tmp_path/'v2_full')
    assert a['model_completions_by_task']['review_assessment']>0
    assert a['model_completions_by_task']['plan_route']>0
    assert 'frontier' in b['model_completions_by_task']
    sheet=(tmp_path/'v2_full'/'manual_review.csv').read_text()
    assert all(c in sheet.split('\n')[0] for c in COLUMNS)
    assert 'reviewer_rationale' in sheet and b['review_status'].startswith('No independent')


def test_preflight_failed_live_mode_never_records_fake_inference(tmp_path,monkeypatch):
    for key in ('OPENROUTER_API_KEY','RCA_LLM_API_KEY','OPENAI_API_KEY'):
        monkeypatch.delenv(key,raising=False)
    status=run_matrix(tmp_path,mode='live',profiles=['v1_prompt_only'])
    assert status['profiles'][0]['run_status']=='failed_or_partial'
    assert status['profiles'][0]['provider_http_completions']==0
    assert status['profiles'][0]['report'] is None
    assert (tmp_path/'v1_prompt_only'/'EXECUTION_FAILED.txt').exists()
