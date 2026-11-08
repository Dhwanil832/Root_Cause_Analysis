"""Intake ablation: pass the model extraction through without normalization.

The later quote-and-identity validation remains mandatory in BOTH policies.
"""
from shared.validation import ProposalError


def normalize(raw):
    if not isinstance(raw,dict):raise ProposalError('Intake extraction must be a JSON object')
    return raw
