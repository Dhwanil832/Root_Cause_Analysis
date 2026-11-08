"""Assessor: semantic proposals, references, impact, and guarded commit through v2."""
from __future__ import annotations
from shared.validation import ProposalError, safe_atom, required_quote, bounded_str, short_id
from revision.v2.kernel import Key

from reasoning.assessor.components.correction_validator import validate_corrections

from reasoning.assessor.components.coverage_validator import validate_resolutions

class AssessorAgentMixin:
    def _validated_corrections(self,source, extraction):
        return validate_corrections(self ,source, extraction)

    def _validated_resolutions(self,source, frontier, new_claims):
        return validate_resolutions(self ,source, frontier, new_claims)

    def _source_route(self,doc_id):
        for attempt in reversed(self.attempts):
            if attempt.get('returned_document')==doc_id:return attempt['route']
        return None

    def assess(self,source,via='initial'):
        if source['id'] in self.session.documents:raise ProposalError('Document already in case')
        state=self.public_state()
        old_claims=state['existing_claims']
        extraction,new_claims=self.extract_document(source,state)
        if not isinstance(extraction,dict):raise ProposalError('Model extraction must be an object')
        corrections=self._validated_corrections(source,extraction)
        new_index=[{**x} for x in new_claims]
        frontier=self.propose_frontier(source,state,new_index)
        if not isinstance(frontier,dict):raise ProposalError('Model frontier must be an object')
        # Independent assessor policy may quarantine model proposals, never add evidence.
        review=self.registry.review_assessment(self,source,state,extraction,frontier,new_claims)
        frontier=review['frontier']
        new_claims=review['new_claims']
        assessment=review['assessment']
        new_gaps,episodes=self._validated_new_gaps(source,frontier)
        coverage=self._validated_resolutions(source,frontier,new_claims)
        rules,mechanisms,deferred=self._validated_inferences(source,frontier,new_claims)
        # Validate all language-model updates before committing the v2 transaction.
        checked_hypotheses=[]
        for h in frontier.get('hypotheses',[]):
            if not isinstance(h,dict):raise ProposalError('Invalid hypothesis object')
            text=bounded_str(h['summary'])
            checked_hypotheses.append({'id':short_id('H_',text.lower()),'summary':text,
                'missing_conditions':[str(x)[:280] for x in h.get('missing_conditions',[])],
                'why':str(h.get('why',''))[:500],
                'tests':[str(x)[:280] for x in h.get('tests',[])],
                'origin_source':source['id'],'status':'candidate_not_proof'})
        revisions=[]
        for item in frontier.get('hypothesis_updates',[]):
            hid=item.get('hypothesis_id')
            if hid not in self.hypotheses:raise ProposalError('Unknown hypothesis to revise')
            if item.get('status') not in {'candidate_not_proof','needs_reassessment','retired'}:
                raise ProposalError('Invalid hypothesis status')
            quote=required_quote(item.get('quote'),source['text'])
            revisions.append({'hypothesis_id':hid,'status':item['status'],
                              'quote':quote,'reason':bounded_str(item['reason'])})
        # Both model responses and all updates have been validated first.
        # Raw intake and interpreted kernel mutations are then committed together.
        self.controller.ingest(self.session,source,via)
        before_episode_count=len(self.session.episodes)
        proposal={'document':source['id'],'actor':self.last_model_name,
                  'observations':[{'key':x['key'],'basis':x['basis'],'positive':x['positive'],
                                   'citations':[{'document':source['id'],'quote':x['quote']}]} for x in new_claims],
                  'corrections':corrections,'new_episodes':episodes,'coverage':coverage,
                  'rules':rules,'mechanisms':mechanisms,
                  'review_note':'Model-produced interpretations; exact quotes checked, semantic entailment and physical causality NOT independently verified.'}
        self.controller.commit(self.session,proposal)
        for item in new_claims:
            if item['claim_id'] not in self.claims:self.claims[item['claim_id']]=item
        for inference in rules:
            key=Key.parse(inference['conclusion'])
            inference_id=short_id('C_',key.label())
            if inference_id not in self.claims:
                self.claims[inference_id]={'claim_id':inference_id,'semantic_label':'qualified_'+key.proposition,
                   'subject':key.subject,'predicate':key.proposition,'scope':key.event_scope,
                   'configuration':key.configuration,'key':key.label(),'quote':inference['warrant'],
                   'basis':'model_assessed_inference','positive':True,'first_source':source['id']}
                self.inference_ids.add(inference_id)
        for gap,episode in zip(new_gaps,self.session.episodes[before_episode_count:]):
            gap['need_id']=episode['need']
            self.gaps[gap['id']]=gap
        for h in checked_hypotheses:
            if h['id'] not in self.hypotheses:self.hypotheses[h['id']]=h
        for item in revisions:
            target=self.hypotheses[item['hypothesis_id']]
            target['status']=item['status']
            target.setdefault('revisions',[]).append({'source':source['id'],'quote':item['quote'],
                                                      'reason':item['reason']})
        auto_flags=self.registry.postcommit_impact(self,corrections)
        self.assessment_history.append({'source':source['id'],**assessment})
        self._refresh_gaps()
        self.record('source_assessed',source=source['id'],via=via,
                    observation_count=len(new_claims),correction_targets=[x['target'] for x in corrections],
                    rules_added=[x['id'] for x in rules],hypotheses_reassessed=[x['hypothesis_id'] for x in revisions],
                    new_gaps=[x['semantic_label'] for x in new_gaps],
                    auto_reassessment_flags=auto_flags, assessor_review=assessment, deferred_inferences=deferred)

