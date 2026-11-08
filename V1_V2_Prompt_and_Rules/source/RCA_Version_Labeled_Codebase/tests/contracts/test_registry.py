import pytest
from shared.config_loader import load_config,merge
from shared.registry import ComponentRegistry
from shared.prompt_loader import load
from shared.contracts.agent_inputs import AgentInput
from shared.contracts.agent_outputs import AgentOutput

def test_selected_baseline_is_allowed():
    c=load_config('config/experiments/ablation_no_llm.yaml')
    r=ComponentRegistry(c)
    assert r.selected_name('specialist')=='v1_basic'
    assert r.selected_name('assessor')=='ablation_no_llm'
    assert all(len(v)==64 for v in r.prompt_hashes.values())

def test_all_five_roles_have_prompts():
    c=load_config()
    r=ComponentRegistry(c)
    assert len(r.prompts)==5
    for role in r.prompts:
        assert r.prompt(role).strip()

def test_disallowed_implementation_fails():
    c=load_config()
    c['agents']['specialist']['implementation']='../../private_reference'
    with pytest.raises(ValueError):ComponentRegistry(c)

def test_prompt_path_traversal_fails():
    with pytest.raises(ValueError):load('lead','../../secrets')

def test_agent_output_must_be_json_object():
    with pytest.raises(ValueError):AgentOutput('lead',['not-an-object'])

def test_hidden_gold_fields_blocked():
    with pytest.raises(ValueError):AgentInput('lead','task',{'gold_answer':'leak'})
    with pytest.raises(ValueError):AgentInput('lead','task',{'designer_reference':True})

def test_override_preserves_defaults():
    c=load_config('config/experiments/ablation_v2_frontier_only.yaml')
    assert c['agents']['specialist']['implementation']=='v2_causal_frontier'
    assert c['llm']['provider']=='openrouter'
    assert c['project']['max_actions']==18

def test_prompt_edit_can_change_hash(tmp_path):
    text,sha=load('specialist','v2_causal_frontier')
    import hashlib
    assert sha==hashlib.sha256(text.encode()).hexdigest()
