"""Request shape checks before contacting humans or custodians."""
from shared.validation import ProposalError

def validate_request(question):
    if not isinstance(question,str) or len(question.strip())<12:
        raise ProposalError('Evidence request must state information needed')
    return question.strip()
