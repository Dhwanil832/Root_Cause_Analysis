"""Lead: model-generated candidate actions + interchangeable validated selection policies."""
from __future__ import annotations
from shared.validation import ProposalError
from reasoning.lead.components.action_generator import get_candidates
from reasoning.lead.components.action_selector import select

class LeadAgentMixin:
    def choose(self):
        state=self.public_state()
        result=self.ask_role('lead','propose_actions',state)
        admissible=self.registry.rank_actions(self,get_candidates(result),state)
        choice=select(admissible)
        self.record('decision_selected',selected_action=choice,
                    alternatives=[{'mode':x['action']['mode'],'route':x['action']['route'],
                                   'gap_id':x['action']['gap_id'],'score':x['score'],
                                   'breakdown':x.get('breakdown',{})} for x in admissible],
                    selection_method=self.registry.selected_name('lead')+'_ordinal_heuristic_not_VOI')
        return choice

