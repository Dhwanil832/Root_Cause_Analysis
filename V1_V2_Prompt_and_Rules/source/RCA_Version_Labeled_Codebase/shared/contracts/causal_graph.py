"""Causal proposal is never equivalent to a supported evidence claim."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ProposedCausalLink:
    causes:tuple[str,...]
    effect:str
    rationale:str
    grade:str='hypothesis'
