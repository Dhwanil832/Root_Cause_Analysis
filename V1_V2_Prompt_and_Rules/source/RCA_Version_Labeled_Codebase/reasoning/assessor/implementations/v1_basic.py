"""V1 prompt-only assessor comparator: a second model critique, no V2 scope guard.

The original v2 quote, source/version and request safeguards still apply;
model critique cannot fabricate new state updates or bypass the controller.
"""
from reasoning.assessor.components.proposal_review import apply_review


def review(runtime,source,state,extraction,frontier,new_claims):
    view={'document':source,'existing_claims':state['existing_claims'],
          'new_assertions':new_claims,'existing_hypotheses':state['hypotheses'],
          'proposed_hypotheses':frontier.get('hypotheses',[]),
          'proposed_inferences':frontier.get('inferences',[]),
          'proposed_corrections':extraction.get('corrections',[]),
          'open_information_needs':state['gaps']}
    return apply_review(source,frontier,runtime.ask_role('assessor','review_assessment',view),new_claims)


def postcommit(runtime,corrections):
    return []
