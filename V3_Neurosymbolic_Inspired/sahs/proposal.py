"""Replaceable proposal generator port and validated batch container."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .engine_contracts import (
    CausalRuleCandidate,
    ClarificationItem,
    InformationGap,
    Proposition,
    RejectedFragment,
)


@dataclass(frozen=True, slots=True)
class ProposalRequest:
    assignment_id: str
    task_mode: str
    operation_goal: str
    target_proposition_id: str | None
    context: dict[str, Any]
    # What was left out of ``context`` to fit the prompt budget, item by item.
    omitted: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProposalBatch:
    schema_version: str
    proposed_propositions: tuple[Proposition, ...]
    proposed_rules: tuple[CausalRuleCandidate, ...]
    clarification_items: tuple[ClarificationItem, ...]
    information_gaps: tuple[InformationGap, ...]
    rejected_fragments: tuple[RejectedFragment, ...] = ()


class ProposalGenerator(Protocol):
    def propose(self, request: ProposalRequest) -> dict[str, Any]: ...


class OpenAICompatibleProposalGenerator:
    """Adapt a model exposing ask(task, system, payload) to the SAHS port."""

    def __init__(self, model: Any, system_prompt: str | None = None) -> None:
        from .prompt_builder import SYSTEM_INSTRUCTIONS
        if not callable(getattr(model, "ask", None)):
            raise TypeError("model must expose ask(task, system, payload)")
        self.model = model
        self.system_prompt = system_prompt or SYSTEM_INSTRUCTIONS
        self.calls_made = 0

    def propose(self, request: ProposalRequest) -> dict[str, Any]:
        result = self.model.ask("sahs_proposal", self.system_prompt, request.context)
        self.calls_made += 1
        if not isinstance(result, dict):
            raise ValueError("model returned a non-object SAHS proposal")
        return result
