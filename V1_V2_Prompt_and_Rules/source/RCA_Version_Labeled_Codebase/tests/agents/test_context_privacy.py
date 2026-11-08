import pytest
from reasoning.context.context_builder import build_agent_context


def test_public_context_is_cloned_even_at_nested_levels():
    original={'open_gaps':[{'id':'g','routes_to_consider':[{'route':'security'}]}]}
    copied=build_agent_context(original)
    copied['open_gaps'][0]['routes_to_consider'][0]['route']='wrong'
    assert original['open_gaps'][0]['routes_to_consider'][0]['route']=='security'


def test_nested_designer_reference_cannot_enter_assessor_or_specialist_payload():
    with pytest.raises(ValueError,match='Forbidden private field'):
        build_agent_context({'document':{'id':'IR-01'},'state':{'hidden_documents':['CAM-17']}})
    with pytest.raises(ValueError,match='Forbidden private field'):
        build_agent_context({'frontier':[{'author_only':{'true_cause':'leak'}}]})


def test_document_text_containing_label_does_not_trigger_key_filter():
    p={'document':{'id':'A','text':'The memo says author_only on a screenshot label.'}}
    assert build_agent_context(p)==p
