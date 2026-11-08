from reasoning.specialist.implementations import v1_basic as baseline, v2_causal_frontier as causal_frontier, v2_iris_inspired as iris_inspired


def context():
    return {
        'gaps':[], 'hypotheses':[],
        'new_assertions':[{'quote':'The report identified water next to the machine at 10:05 AM.'}],
        'current_source':{'id':'IR-01','text':'The report identified water next to the machine at 10:05 AM.'},
    }


def test_causal_frontier_rejects_self_support_and_repeated_premises():
    raw={'new_gaps':[],'hypotheses':[],
         'inferences':[{'effect_claim_id':'a','cause_claim_ids':['a'],'premise_claim_ids':['a','b']},
                       {'effect_claim_id':'c','cause_claim_ids':['a'],'premise_claim_ids':['a','a']},
                       {'effect_claim_id':'c','cause_claim_ids':['a'],'premise_claim_ids':['a','b']}]}
    assert len(baseline.transform(raw,context())['inferences'])==3
    out=causal_frontier.transform(raw,context())
    assert len(out['inferences'])==1
    assert {x['reason'] for x in out['deferred_inference_candidates']}=={'cause_equals_effect','repeated_premise'}


def test_iris_inspired_generates_question_only_from_conditional_hypothesis():
    raw={'hypotheses':[{'summary':'Water might come from the coupling',
                        'missing_conditions':['The coupling was disconnected during the shift']}],
         'new_gaps':[{'semantic_label':'floor_origin','kind':'causal','question':'Who controlled floor inspections?',
                      'expected_change':'Identify information about inspection records',
                      'routes_to_consider':[{'route':'maintenance','topic':'service records of the coupling','directness':1,'burden':1}]}],
         'inferences':[]}
    causal=causal_frontier.transform(raw,context())
    extra=iris_inspired.transform(raw,context())
    assert len(causal['new_gaps'])==1
    assert len(extra['new_gaps'])==2
    new=extra['new_gaps'][1]
    assert new['origin']=='automatically_generated_inquiry_not_a_finding'
    assert 'disconnected' in new['question']
    assert new['quote']=='The report identified water next to the machine at 10:05 AM.'
    assert new['routes_to_consider'][0]['route']=='maintenance'
    assert len(extra.get('inferences',[]))==0  # request, not asserted event


def test_no_source_quote_means_no_synthetic_missing_condition():
    raw={'hypotheses':[{'summary':'Possible failure','missing_conditions':['Disconnection of hose at 10:00']}],
         'new_gaps':[{'semantic_label':'g','question':'service data','routes_to_consider':[{'route':'maintenance'}]}]}
    public={'gaps':[], 'hypotheses':[],'new_assertions':[],'current_source':{'id':'IR-01'}}
    assert len(iris_inspired.transform(raw,public)['new_gaps'])==1
