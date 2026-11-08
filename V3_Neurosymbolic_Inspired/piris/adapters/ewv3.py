"""Convert PIRIS material records into the Evidence Worker V3 source contract."""
from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from ewv3.contracts import SourceRepresentation, SourceUnit

from ..contracts import MaterialRecord


def to_ewv3_sources(materials: Iterable[MaterialRecord], *,
                    index_status_by_material: dict[str, str] | None = None
                    ) -> tuple[SourceUnit, ...]:
    """Export searchable materials; each source keeps its version and source map."""
    statuses = index_status_by_material or {}
    result = []
    for material in materials:
        extraction = material.extraction
        status = statuses.get(material.material_id, material.index_status)
        searchable = status == "ready" and extraction.status in {"ready", "partial"}
        if not searchable:
            continue
        representation_id = (
            f"{material.material_id}:{extraction.parser_name}:{extraction.parser_version}"
        )
        source_map = tuple({
            "segment_id": segment.segment_id,
            "text": segment.text,
            "location": asdict(segment.location),
        } for segment in extraction.segments)
        representation = SourceRepresentation(
            representation_id=representation_id,
            modality="text",
            text=extraction.text,
            structural_context={
                "source_map": source_map,
                "parser_name": extraction.parser_name,
                "parser_version": extraction.parser_version,
            },
            content_ref=f"material:{material.material_id}",
            searchable=True,
            readiness="ready",
        )
        result.append(SourceUnit(
            source_id=material.material_id,
            source_version=material.version_id,
            representation_id=representation_id,
            title=material.filename or material.material_id,
            text=extraction.text,
            source_kind=material.declared_kind or "case_material",
            searchable=True,
            readiness="ready",
            origin="case_submission",
            lineage="submitter_provided",
            metadata={
                "content_digest": material.content_digest,
                "revision_of": material.revision_of,
                "submission_ids": material.submission_ids,
                "parser_name": extraction.parser_name,
                "parser_version": extraction.parser_version,
            },
            representations=(representation,),
        ))
    return tuple(result)

