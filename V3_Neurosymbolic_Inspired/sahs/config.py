"""Hard, auditable resource limits for a SAHS run."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpecialistConfig:
    max_source_chars: int = 24000
    max_propositions: int = 40
    max_rules: int = 40
    max_candidates: int = 12
    max_depth: int = 3
    max_answer_sets: int = 64
    solver_timeout_seconds: float = 2.0
    max_targeted_expansion_calls: int = 1
    max_returned_explanations: int = 3
    # Estimated prompt tokens a proposal call may use; the rest of the model's
    # context window is left for its reasoning and answer. None: no limit.
    max_prompt_tokens: int | None = None

    def __post_init__(self) -> None:
        integer_limits = (
            self.max_propositions, self.max_rules, self.max_candidates,
            self.max_depth, self.max_answer_sets, self.max_targeted_expansion_calls,
            self.max_returned_explanations,
        )
        if any(value < 1 for value in integer_limits):
            raise ValueError("Specialist integer limits must be positive")
        if self.max_source_chars < 1 or self.solver_timeout_seconds <= 0:
            raise ValueError("source and solver limits must be positive")
        if self.max_prompt_tokens is not None and self.max_prompt_tokens < 1:
            raise ValueError("max_prompt_tokens must be positive")
        if self.max_targeted_expansion_calls > 1:
            raise ValueError("SAHS currently permits at most one targeted expansion call")
