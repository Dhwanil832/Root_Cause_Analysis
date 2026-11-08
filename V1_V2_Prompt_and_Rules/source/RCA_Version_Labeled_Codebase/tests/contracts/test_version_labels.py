"""Version naming is an executable contract, not documentation only."""
from pathlib import Path
import pytest
from shared.config_loader import ROOT, load_config
from shared.registry import ComponentRegistry, IMPLEMENTATIONS, PATHS
from evaluation.run_matrix import PROFILES


def test_every_algorithm_has_matching_version_labeled_prompt_file():
    for role, implementations in IMPLEMENTATIONS.items():
        rel=Path(*PATHS[role].split('.'))
        for implementation in implementations:
            assert implementation.startswith(('v1_', 'v2_', 'ablation_'))
            assert (ROOT / rel / 'implementations' / (implementation + '.py')).exists()
            assert (ROOT / rel / 'prompts' / (implementation + '.md')).exists()
        assert 'v1_basic' in implementations
        assert not any(x.startswith('v3_') for x in implementations)


def test_experiment_v1_and_v2_full_are_unambiguous():
    v1=ComponentRegistry(load_config('config/experiments/v1_basic.yaml'))
    v2=ComponentRegistry(load_config('config/experiments/v2_full.yaml'))
    assert all(v1.selected_name(role)=='v1_basic' for role in PATHS)
    assert all(v2.selected_name(role).startswith('v2_') for role in PATHS)
    assert all(v1.prompt_variants[role]=='v1_basic' for role in PATHS)
    assert all(v2.prompt_variants[role].startswith('v2_') for role in PATHS)


def test_factorial_ablations_intentionally_cross_prompts_and_methods():
    prompts=ComponentRegistry(load_config('config/experiments/v2_prompts_only.yaml'))
    methods=ComponentRegistry(load_config('config/experiments/v2_methods_only.yaml'))
    for role in PATHS:
        assert prompts.selected_name(role)=='v1_basic'
        assert prompts.prompt_variants[role].startswith('v2_')
        assert methods.selected_name(role).startswith('v2_')
        assert methods.prompt_variants[role]=='v1_basic'


def test_non_generating_ablation_is_not_mislabeled_as_v1():
    no_llm=ComponentRegistry(load_config('config/experiments/ablation_no_llm.yaml'))
    assert no_llm.selected_name('evidence_worker')=='ablation_no_llm'
    assert no_llm.selected_name('assessor')=='ablation_no_llm'
    for role in ('intake','specialist','lead'):
        assert no_llm.selected_name(role)=='v1_basic'


def test_all_experiment_configs_are_loadable():
    for path in sorted((ROOT/'config/experiments').glob('*.yaml')):
        ComponentRegistry(load_config(path))
    assert all(Path(profile).is_file() or (ROOT/profile).is_file() for profile in PROFILES.values())
