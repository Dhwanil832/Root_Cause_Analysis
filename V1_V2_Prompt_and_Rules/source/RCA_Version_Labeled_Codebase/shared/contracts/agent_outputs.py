"""Input/output validation contract shared by all swappable role policies."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class AgentOutput:
    role:str
    proposal:dict[str,Any]
    def __post_init__(self):
        if not isinstance(self.proposal,dict):raise ValueError('An agent must return a JSON object')
