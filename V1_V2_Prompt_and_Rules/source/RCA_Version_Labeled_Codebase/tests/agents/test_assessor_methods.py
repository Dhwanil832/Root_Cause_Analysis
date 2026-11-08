import pytest
from shared.validation import ProposalError
from reasoning.assessor.components.proposal_review import apply_review
from reasoning.assessor.implementations import ablation_no_llm as baseline

SOURCE={'id':'DOC-1','text':'The valve was closed on the control panel, but flow was measured at the outlet.'}
FRONTIER={'hypotheses':[{'summary':'A leak may have contributed','missing_conditions':[]}],
          'inferences':[{'warrant':'Control closed means sealed'},{'warrant':'Qualified conditional relation'}],
          'new_gaps':[]}


def test_assessor_exclusion_requires_verbatim_evidence_and_selects_exact_proposal():
    response={'exclude_inference_indices':[0], 'exclude_hypothesis_summaries':[],
      'flags':[{'kind':'entailment','quote':'valve was closed on the control panel',
                'reason':'Indication alone does not establish a sealed valve'}]}
    out=apply_review(SOURCE,FRONTIER,response)
    assert out['frontier']['inferences']==[FRONTIER['inferences'][1]]
    assert len(FRONTIER['inferences'])==2  # no input mutation
    assert out['assessment']['model_review_performed']
    base=baseline.review(None,SOURCE,{},None,FRONTIER,[])
    assert len(base['frontier']['inferences'])==2
    assert not base['assessment']['model_review_performed']


def test_assessor_cannot_quarantine_without_source_grounded_reason():
    response={'exclude_inference_indices':[0], 'exclude_hypothesis_summaries':[], 'flags':[]}
    with pytest.raises(ProposalError,match='source-grounded'):
        apply_review(SOURCE,FRONTIER,response)


def test_assessor_cannot_invent_claims_or_corrupt_evidence_state():
    with pytest.raises(ProposalError,match='unsupported mutation'):
        apply_review(SOURCE,FRONTIER,{'exclude_inference_indices':[], 'new_fact':'valve leaked'})
    with pytest.raises(ProposalError,match='verbatim source substring'):
        apply_review(SOURCE,FRONTIER,{'exclude_inference_indices':[0],
             'flags':[{'kind':'entailment','quote':'leak occurred exactly at 10:00',
                       'reason':'Invented measurement'}]})


def test_assessor_can_quarantine_a_specific_wrongly_scoped_observation():
    source={'id':'S','text':'The late bench test showed a leak. Incident-time leakage was not measured.'}
    claims=[{'semantic_label':'instant_leak','claim_id':'id1'},
            {'semantic_label':'bench_leak','claim_id':'id2'}]
    response={'exclude_assertion_labels':['instant_leak'],
              'flags':[{'kind':'scope','quote':'Incident-time leakage was not measured.',
                         'reason':'Later bench observation cannot establish an incident measurement'}]}
    answer=apply_review(source,{'hypotheses':[],'inferences':[]},response,claims)
    assert [x['semantic_label'] for x in answer['new_claims']]==['bench_leak']
    assert answer['assessment']['excluded_assertion_labels']==['instant_leak']
    assert len(claims)==2
