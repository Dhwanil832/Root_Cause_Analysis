"""Validate that the LLM proposed candidate actions, not privileged file IDs."""
from shared.validation import ProposalError

def get_candidates(result):
    if not isinstance(result,dict) or not isinstance(result.get('actions'),list):
        raise ProposalError('Planner requires an actions list')
    return result['actions'][:20]
