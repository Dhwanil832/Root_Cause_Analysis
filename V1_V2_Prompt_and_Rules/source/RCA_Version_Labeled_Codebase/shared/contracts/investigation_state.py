"""Read-only case context passed to agents, not an editable case database."""
from dataclasses import dataclass

@dataclass(frozen=True)
class InvestigationView:
    case_id:str
    claims:tuple
    hypotheses:tuple
    open_gaps:tuple
