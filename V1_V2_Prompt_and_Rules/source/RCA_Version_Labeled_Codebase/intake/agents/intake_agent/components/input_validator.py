"""Validate a delivered source shape; require no predefined 'unknown' list."""
from shared.validation import ProposalError

def validate_source(source):
    if not isinstance(source,dict):raise ProposalError('Source must be an object')
    for key in ('id','text','title'):
        if not isinstance(source.get(key),str) or not source[key].strip():
            raise ProposalError(f'Missing document {key}')
    if len(source['text'])>5_000_000:raise ProposalError('Document too large')
    return source
