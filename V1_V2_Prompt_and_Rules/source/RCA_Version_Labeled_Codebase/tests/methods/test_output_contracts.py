"""A model reply is not accepted just because it parses as JSON."""
import copy
import pytest
from shared.contracts.task_validation import validate,TaskContractError
from shared.llm.fixture import FixtureModel
from orchestration.orchestrator import Investigator
from shared.config_loader import load_config,ROOT
from integrations.evidence_sources.synthetic_world import EvidenceWorld


def test_quote_that_is_not_in_source_is_rejected():
    answer={'assertions':[{'semantic_label':'x','subject':'x','predicate':'x','scope':'x',
             'configuration':'reported','basis':'assessed_source_assertion',
             'quote':'This is an invented quote.'}], 'corrections':[]}
    with pytest.raises(TaskContractError,match='exact substring'):
        validate('extract',answer,{'document':{'id':'S','text':'No such statement is here.'}})


def test_missing_arrays_get_explicit_errors():
    with pytest.raises(TaskContractError,match='hypotheses'):
        validate('frontier',{'new_gaps':[]},{'document':{'text':'A real event happened.'}})
    with pytest.raises(TaskContractError,match='actions'):
        validate('propose_actions',{'actions':'none'}, {})
    with pytest.raises(TaskContractError,match='assessor'):
        validate('review_assessment',{'flags':None}, {'document':{'text':'Original.'}})


class OnceWrongThenCorrect(FixtureModel):
    def __init__(self,p):
        super().__init__(p)
        self.repaired=False
    def ask(self,task,system,payload):
        result=super().ask(task,system,payload)
        if task=='extract' and payload['document']['id']=='IR-01':
            if '_contract_repair_feedback' not in payload:
                result['assertions'][0]['quote']='This citation is not in the document.'
            else:
                self.repaired=True
                assert 'exact substring' in payload['_contract_repair_feedback']['error']
        return result


def test_structural_retry_repairs_without_answer_oracle():
    model=OnceWrongThenCorrect(ROOT/'evaluation/private_reference/fixture_responses_DESIGNER_ONLY.json')
    investigator=Investigator(EvidenceWorld(ROOT/'evaluation/fixtures/wet_floor/documents.json'),
        load_config('config/experiments/ablation_no_llm.yaml'),mode='fixture',model=model,max_steps=1)
    investigator.run()
    assert model.repaired
    assert len(investigator.contract_rejections)==1
    assert investigator.contract_rejections[0]['task']=='extract'
    assert 'IR-01' in investigator.session.documents
    assert sum(r.actual_call_performed for r in investigator.model_calls)==0
