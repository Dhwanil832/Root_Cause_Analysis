"""Minimal host-facing context contracts; no private-reference fields allowed."""
from __future__ import annotations
from dataclasses import dataclass,field
from typing import Any

@dataclass(frozen=True)
class AgentInput:
    role:str
    task:str
    public_context:dict[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        if self.role not in {'intake','specialist','lead','evidence_worker','assessor'}:
            raise ValueError('Unexpected agent role')
        if 'designer_reference' in self.public_context or 'gold_answer' in self.public_context:
            raise ValueError('Private reference materials cannot be passed as agent context')
