"""Intake agent: only processes delivered raw documents."""
from __future__ import annotations
from shared.validation import ProposalError, safe_atom, required_quote, short_id
from revision.v2.kernel import Key
from intake.agents.intake_agent.components.input_validator import validate_source

from intake.agents.intake_agent.components.assertion_validator import validate_assertions

class IntakeAgentMixin:
    def _validated_assertions(self,source, extraction):
        return validate_assertions(self ,source, extraction)


    def extract_document(self, source, state):
        validate_source(source)
        proposal=self.ask_role('intake','extract',{
            'neutral_case_description':state['focal_event'],
            'document':source,'existing_claims':state['existing_claims']})
        if not isinstance(proposal,dict):
            raise ProposalError('Intake must return an object')
        proposal=self.registry.normalize_intake(proposal)
        self.intake_history.append({'source':source['id'],
                                   **proposal.get('_intake_audit',{'policy':'baseline','flags':[],
                                     'semantic_entailment_verified':False})})
        return proposal, self._validated_assertions(source,proposal)
