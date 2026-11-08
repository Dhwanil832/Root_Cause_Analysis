"""Hard resource bounds for a HERA1 run."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AssessorConfig:
    max_materials: int = 12
    max_total_material_chars: int = 48_000
    max_hypothesis_parts: int = 24
    max_extracted_statements: int = 48
    max_context_chars: int = 8_000
    max_answer_chars: int = 6_000
    max_request_chars: int = 1_500
    max_request_history: int = 100
    max_related_answers: int = 20
    max_request_revisions: int = 1
    max_model_calls_evidence: int = 2
    max_model_calls_other: int = 1
    # Extra attempts after a reply fails validation. The fixed per-task call
    # limits above describe the normal path; each retry is an additional call
    # and is counted in the result's ``model_calls``. Off by default.
    max_output_retries: int = 0
    # Reuse a completed evidence judgment when an identical claim and passage are
    # assessed again (for example for another information need). Off by default.
    reuse_identical_judgments: bool = False

    def __post_init__(self) -> None:
        positive = (
            self.max_materials, self.max_total_material_chars,
            self.max_hypothesis_parts, self.max_extracted_statements,
            self.max_context_chars, self.max_answer_chars,
            self.max_request_chars, self.max_request_history,
            self.max_related_answers,
        )
        if any(value < 1 for value in positive):
            raise ValueError("HERA1 limits must be positive")
        if self.max_request_revisions < 0 or self.max_output_retries < 0:
            raise ValueError("max_request_revisions and max_output_retries cannot be negative")
        if self.max_model_calls_evidence != 2 or self.max_model_calls_other != 1:
            raise ValueError("HERA1 call limits are fixed at two evidence calls and one other-task call")
