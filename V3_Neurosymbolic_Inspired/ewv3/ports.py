"""Replaceable model and corpus-retrieval ports."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .contracts import EvidenceAssignment, SourceRepresentation, SourceUnit


@dataclass(frozen=True, slots=True)
class SearchHit:
    source_id: str
    representation_id: str
    start_offset: int | None
    end_offset: int | None
    score: float
    channel: str
    excerpt: str = ""
    structural_context: dict[str, Any] | None = None
    modality: str = "text"
    channels: tuple[str, ...] = ()
    score_semantics: str = "retrieval_rank_only"


class EvidencePlanner(Protocol):
    def plan_queries(self, assignment: EvidenceAssignment) -> dict[str, Any]: ...
    def refine_queries(self, assignment: EvidenceAssignment,
                       unresolved_slot_ids: tuple[str, ...],
                       slot_summaries: tuple[dict[str, Any], ...]) -> dict[str, Any]: ...
    def draft_requests(self, assignment: EvidenceAssignment, unresolved_slot_ids: tuple[str, ...],
                       slot_summaries: tuple[dict[str, Any], ...]) -> dict[str, Any]: ...


class CorpusRetriever(Protocol):
    version: str

    def search(self, query: str, *, channel: str, sources: tuple[SourceUnit, ...],
               limit: int) -> tuple[SearchHit, ...]: ...


class TextEmbedder(Protocol):
    """Injected local or hosted embedding model; vectors stay inside the adapter."""
    version: str

    def embed(self, text: str) -> tuple[float, ...]: ...
    def embed_query(self, text: str) -> tuple[float, ...]: ...
    def embed_document(self, text: str) -> tuple[float, ...]: ...


class ImageTextEmbedder(Protocol):
    """Shared-space image/text model for retrieving original visual regions."""
    version: str

    def embed_text(self, text: str) -> tuple[float, ...]: ...
    def embed_image(self, content_ref: str,
                    structural_context: dict[str, Any]) -> tuple[float, ...]: ...


class CandidateReranker(Protocol):
    """Optional reranker over already retrieved, provenance-bearing passages."""
    version: str

    def rerank(self, query: str, hits: tuple[SearchHit, ...], *,
               sources: tuple[SourceUnit, ...], limit: int) -> tuple[SearchHit, ...]: ...

