import pytest
from shared.validation import ProposalError
from intake.agents.intake_agent.implementations import v1_basic as baseline, v2_structured_llm as structured_llm


def assertion(label,subject='F2',predicate='floor_wet',positive=True,basis='assessed_source_assertion',quote='Water was present near F-2'):
    return {'semantic_label':label,'subject':subject,'predicate':predicate,'scope':'10_05',
            'configuration':'incident','polarity':positive,'basis':basis,'quote':quote}


def test_structured_deduplicates_same_scoped_claim_but_baseline_does_not():
    raw={'assertions':[assertion('floor_wet'),assertion('same','F2')], 'corrections':[]}
    b=baseline.normalize(raw)
    e=structured_llm.normalize(raw)
    assert len(b['assertions'])==2
    assert len(e['assertions'])==1
    assert e['_intake_audit']['flags'][0]['kind']=='duplicate_assertion'
    assert len(raw['assertions'])==2  # no input mutation


def test_structured_rejects_reused_semantic_label_with_different_scoped_identity():
    raw={'assertions':[assertion('x'),assertion('x',subject='F4')]}
    assert len(baseline.normalize(raw)['assertions'])==2
    with pytest.raises(ProposalError,match='semantic label'):
        structured_llm.normalize(raw)


def test_structured_rejects_unscoped_conflicting_claims_from_one_document():
    raw={'assertions':[assertion('wet',positive=True),assertion('dry',positive=False)]}
    with pytest.raises(ProposalError,match='Contradictory'):
        structured_llm.normalize(raw)


def test_modality_warning_is_a_flag_not_fabricated_evidence():
    raw={'assertions':[assertion('leak',basis='documented_measurement',
                               quote='Possible leakage was noted near F-2')]}
    out=structured_llm.normalize(raw)
    assert out['assertions']==raw['assertions']
    assert out['_intake_audit']['flags'][0]['kind']=='measurement_without_numeric_quote'
    assert out['_intake_audit']['semantic_entailment_verified'] is False
