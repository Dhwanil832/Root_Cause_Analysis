"""Author-supplied TEST DOUBLE, explicitly NOT a live language model."""
from __future__ import annotations
import json,copy
from pathlib import Path
from shared.llm.client import CallRecord,ModelFailure

class FixtureModel:
    """Deterministic test double, NOT a general intelligence or live-model run.

    It serves authored test labels and synthetic action proposals based on the
    agent's *visible* state. It cannot see the hidden custodian inventory or
    later documents; future document IDs are looked up only after delivery.
    """
    def __init__(self, response_path):
        from pathlib import Path
        self.templates=json.loads(Path(response_path).read_text())
        self.calls=[]

    def ask(self,task,system,payload):
        import copy
        if task in {'extract','frontier'}:
            source_id=payload['document']['id']
            result=copy.deepcopy(self.templates[source_id][task])
            if task=='extract':
                # Claims in corrections come by semantic ID in the template; the
                # model never gets a future document in its working context.
                for correction in result.get('corrections',[]):
                    if 'target_label' in correction:
                        label=correction.pop('target_label')
                        found=[x for x in payload.get('existing_claims',[]) if x.get('semantic_label')==label]
                        correction['target_claim_ids']=[x['claim_id'] for x in found]
            else:
                # Map authored *labels* to the ID values calculated by the
                # application from visible assertions and earlier claims.
                choices=payload.get('existing_claims',[])+payload.get('new_assertions',[])
                label_to_id={c['semantic_label']:c['claim_id'] for c in choices}
                for update in result.get('hypothesis_updates',[]):
                    if 'hypothesis_contains' in update:
                        phrase=update.pop('hypothesis_contains')
                        matched=[h for h in payload.get('hypotheses',[]) if phrase.lower() in h['summary'].lower()]
                        update['hypothesis_id']=matched[0]['id'] if matched else 'not_found'
                for r in result.get('resolved_gaps',[]):
                    if 'gap_label' in r:
                        label=r.pop('gap_label')
                        matching=[g for g in payload.get('gaps',[]) if g['semantic_label']==label]
                        r['gap_id']=matching[0]['id'] if matching else 'not_found'
                for inf in result.get('inferences',[]):
                    if 'premise_labels' in inf:
                        inf['premise_claim_ids']=[label_to_id[x] for x in inf.pop('premise_labels') if x in label_to_id]
                    if 'cause_labels' in inf:
                        inf['cause_claim_ids']=[label_to_id[x] for x in inf.pop('cause_labels') if x in label_to_id]
                    if 'effect_label' in inf:
                        inf['effect_claim_id']=label_to_id.get(inf.pop('effect_label'),'')
        elif task=='review_assessment':
            # Authored no-objection double, NOT a semantic review by a model.
            result={'exclude_inference_indices':[], 'exclude_hypothesis_summaries':[],
                    'exclude_assertion_labels':[],
                    'flags':[], 'reason':'Fixture authored no-objection review; not model validation'}
        elif task=='plan_route':
            # Authored acceptance of lead candidate, NOT route reasoning.
            action=payload['proposed_action']
            result={'decision':'execute','route':action['route'],
                    'question':action.get('question',''),
                    'information_needed':action['information_needed'],
                    'reason':'Fixture follows the lead-selected action'}
        elif task=='propose_actions':
            result={'actions':[]}
            known_routes={x['id'] for x in payload['routes']}
            attempted={(x['gap_id'],x['route']) for x in payload['attempts']}
            # The fixture supplies *candidate* routes per gap; algorithm makes
            # actual selection based on public knowledge and current needs.
            for gap in payload['gaps']:
                if gap['status']!='open':continue
                for q in gap.get('routes_to_consider',[]):
                    route=q['route'];mode='request' if route in known_routes else 'discover'
                    if (gap['id'],route) in attempted:continue
                    result['actions'].append({'mode':mode,'gap_id':gap['id'],'route':route,
                        'question':gap['question'],'possible_effect':gap['expected_change'],
                        'information_needed':q['topic'], 'explanation':gap.get('why',''),
                        'directness':q.get('directness',1),'burden':q.get('burden',1)})
            if not result['actions']:result['actions']=[{'mode':'wait','gap_id':'', 'route':'', 'question':'',
                                                        'possible_effect':'', 'information_needed':'',
                                                        'explanation':'No unattempted route remains.',
                                                        'directness':0,'burden':0}]
        else:raise ModelFailure('Unsupported fixture-model task: '+task)
        self.calls.append(CallRecord(task,'authored_fixture_test_double','fixture',False,0,{},copy.deepcopy(result)))
        return result
