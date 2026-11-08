"""Hard limits for bounded Evidence Worker runs."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkerConfig:
    channels: tuple[str, ...] = ("exact", "lexical")
    max_queries_per_slot: int = 3
    max_candidates_per_slot: int = 8
    max_request_drafts: int = 4
    max_sources: int = 500
    max_text_chars: int = 80_000
    max_query_calls: int = 2
    max_request_calls: int = 1
    max_revisions: int = 2
    max_followup_plans: int = 1
    max_followup_queries_per_slot: int = 2
    # Candidates gathered across queries for one slot, ranked, before grading.
    max_links_for_grading: int = 16
    # The model under test grades each candidate 0-3; only min_grade and above
    # reach the Assessor, at most max_assessed_per_slot per slot.
    grade_candidates: bool = True
    min_grade: int = 2
    max_assessed_per_slot: int = 6

    def __post_init__(self) -> None:
        if not self.channels or any(c not in {"exact", "lexical", "bm25", "semantic", "hybrid"} for c in self.channels):
            raise ValueError("channels must contain exact, lexical, bm25, semantic, or hybrid retrieval")
        for name in ("max_queries_per_slot", "max_candidates_per_slot", "max_sources",
                     "max_text_chars", "max_revisions", "max_followup_queries_per_slot",
                     "max_links_for_grading", "max_assessed_per_slot"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be positive")
        if self.max_request_drafts < 0:
            raise ValueError("max_request_drafts cannot be negative")
        if self.max_query_calls < 1:
            raise ValueError("max_query_calls must allow the required query-planning call")
        if self.max_request_calls < 0:
            raise ValueError("max_request_calls cannot be negative")
        if self.min_grade not in {1, 2, 3}:
            raise ValueError("min_grade must be 1, 2 or 3")
        if self.max_followup_plans not in {0, 1}:
            raise ValueError("max_followup_plans must be 0 or 1 to keep refinement bounded")

