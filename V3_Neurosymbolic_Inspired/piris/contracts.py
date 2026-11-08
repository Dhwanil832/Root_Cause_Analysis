"""Public, dependency-free contracts for PIRIS Intake."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class IntakeState(StrEnum):
    RECEIVED = "received"
    REGISTERED = "registered"
    READY = "ready"
    PARTIAL = "partial"
    FAILED = "failed"


class LinkBasis(StrEnum):
    SUBMITTER_DECLARED = "submitter_declared"
    MODEL_SUGGESTED = "model_suggested"


@dataclass(frozen=True, slots=True)
class RequestReference:
    request_id: str
    description: str = ""
    status: str = "pending"


@dataclass(frozen=True, slots=True)
class IncomingItem:
    """One item in a submission. Content is preserved byte-for-byte."""
    item_id: str
    content: bytes
    media_type: str = "application/octet-stream"
    filename: str = ""
    declared_kind: str = ""
    declared_request_id: str | None = None
    declared_revision_of: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def text(cls, item_id: str, text: str, *, media_type: str = "text/plain",
             filename: str = "", declared_kind: str = "",
             declared_request_id: str | None = None,
             declared_revision_of: str | None = None,
             metadata: dict[str, Any] | None = None) -> "IncomingItem":
        return cls(item_id, text.encode("utf-8"), media_type, filename,
                   declared_kind, declared_request_id, declared_revision_of,
                   metadata or {})


@dataclass(frozen=True, slots=True)
class IntakeAssignment:
    schema_version: str
    case_id: str
    case_snapshot_id: str
    submission_id: str
    received_at: str
    items: tuple[IncomingItem, ...]
    sender_id: str = ""
    request_catalog: tuple[RequestReference, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SourceLocation:
    page: int | None = None
    section: str = ""
    table: str = ""
    region: str = ""
    start_offset: int | None = None
    end_offset: int | None = None
    locator: str = ""


@dataclass(frozen=True, slots=True)
class ExtractedSegment:
    segment_id: str
    text: str
    location: SourceLocation = SourceLocation()


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    status: str  # ready | partial | unsupported | failed
    text: str = ""
    segments: tuple[ExtractedSegment, ...] = ()
    parser_name: str = ""
    parser_version: str = ""
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class InterpretationRequest:
    item_id: str
    filename: str
    media_type: str
    declared_kind: str
    extracted_text: str


@dataclass(frozen=True, slots=True)
class ItemSuggestion:
    item_id: str
    suggested_kind: str = ""
    request_ids: tuple[str, ...] = ()
    note: str = ""


@dataclass(frozen=True, slots=True)
class LinkRecord:
    request_id: str
    basis: LinkBasis
    request_status_at_intake: str
    note: str = ""


@dataclass(frozen=True, slots=True)
class SubmissionItemRecord:
    item_id: str
    material_id: str
    content_digest: str
    media_type: str
    filename: str
    declared_kind: str
    suggested_kind: str = ""
    links: tuple[LinkRecord, ...] = ()
    declared_revision_of: str | None = None
    revision_link_status: str = "none"
    exact_duplicate_content: bool = False
    extraction_status: str = "pending"
    index_status: str = "pending"
    quarantined: bool = False
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MaterialRecord:
    material_id: str
    case_id: str
    content_digest: str
    media_type: str
    filename: str
    declared_kind: str
    content: bytes
    version_id: str
    revision_of: str | None
    extraction: ExtractionResult
    submission_ids: tuple[str, ...] = ()
    created_at: str = ""
    index_status: str = "pending"


@dataclass(frozen=True, slots=True)
class MaterialArrivalEvent:
    event_id: str
    case_id: str
    case_snapshot_id: str
    submission_id: str
    received_at: str
    sender_id: str
    state: IntakeState
    item_records: tuple[SubmissionItemRecord, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MaterialProcessingUpdate:
    """Follow-up notification when asynchronous extraction/indexing completes."""
    event_id: str
    case_id: str
    material_id: str
    version_id: str
    submission_ids: tuple[str, ...]
    processing_stage: str
    status: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class IntakeResult:
    schema_version: str
    submission_id: str
    event: MaterialArrivalEvent
    materials: tuple[MaterialRecord, ...]
    diagnostics: tuple[str, ...] = ()
    resource_usage: dict[str, int] = field(default_factory=dict)

