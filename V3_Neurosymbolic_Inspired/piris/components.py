"""Small default components; real PDF/OCR/model services are injected."""
from __future__ import annotations

from dataclasses import dataclass
import re

import docstruct

from .contracts import ExtractedSegment, ExtractionResult, IncomingItem, SourceLocation

VISUAL_MEDIA_PREFIXES = ("image/", "video/")
VISUAL_MEDIA_TYPES = frozenset({"application/pdf", "image/svg+xml", "application/vnd.dwg", "image/vnd.dwg"})
_EMBEDDED_VISUAL = re.compile(r"!\[[^\]]*\]\([^)]*\)|<img\b|<figure\b", re.IGNORECASE)
NEEDS_VISION = "needs_vision_model"


def needs_vision(media_type: str) -> bool:
    return media_type.startswith(VISUAL_MEDIA_PREFIXES) or media_type in VISUAL_MEDIA_TYPES


class TextContentParser:
    version = "utf8-text-1"

    def parse(self, item: IncomingItem) -> ExtractionResult:
        if not (item.media_type.startswith("text/") or item.media_type == "application/json"):
            return ExtractionResult(status="unsupported", parser_name="TextContentParser",
                                    parser_version=self.version,
                                    warnings=(f"no_parser_for:{item.media_type}",))
        try:
            text = item.content.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return ExtractionResult(status="failed", parser_name="TextContentParser",
                                    parser_version=self.version,
                                    warnings=("utf8_decode_failed",))
        if not text:
            return ExtractionResult(status="partial", text="", parser_name="TextContentParser",
                                    parser_version=self.version, warnings=("empty_text",))
        segment = ExtractedSegment(
            segment_id=f"{item.item_id}:text:0", text=text,
            location=SourceLocation(start_offset=0, end_offset=len(text), locator="text:0"),
        )
        return ExtractionResult(status="ready", text=text, segments=(segment,),
                                parser_name="TextContentParser", parser_version=self.version)


class StructuredTextParser(TextContentParser):
    """Text parser that also records the document's structure as segments.

    The extracted text is the original text, unchanged; each segment is one
    passage (sentence, table row, heading, details line) with exact offsets, its
    section, and, for table rows, the table header.
    """
    version = f"structured-text-1+{docstruct.VERSION}"

    def parse(self, item: IncomingItem) -> ExtractionResult:
        result = super().parse(item)
        if result.status != "ready":
            return result
        structure = docstruct.parse(result.text)
        segments = tuple(ExtractedSegment(
            segment_id=f"{item.item_id}:{p.kind}:{p.index}", text=p.text,
            location=SourceLocation(section=p.section, table=" | ".join(p.table_header),
                                    start_offset=p.start, end_offset=p.end,
                                    locator=f"{p.kind}:{p.index}"),
        ) for p in structure.passages) or result.segments
        warnings = result.warnings
        if _EMBEDDED_VISUAL.search(result.text):
            warnings = (*warnings, f"{NEEDS_VISION}:embedded_image_reference")
        return ExtractionResult(status="ready", text=result.text, segments=segments,
                                parser_name="StructuredTextParser", parser_version=self.version,
                                warnings=warnings)


class ParserRouter:
    """Routes by media type; unknown formats remain registered but unsearchable."""
    def __init__(self, parsers=None) -> None:
        self.parsers = dict(parsers or {})
        self.text_parser = StructuredTextParser()

    def parse(self, item: IncomingItem) -> ExtractionResult:
        parser = self.parsers.get(item.media_type)
        if parser is None and item.media_type.startswith("text/"):
            parser = self.text_parser
        if parser is None and item.media_type == "application/json":
            parser = self.text_parser
        if parser is None:
            warnings = (f"no_parser_for:{item.media_type}",)
            if needs_vision(item.media_type):
                # Not "no evidence here": the content is unread until a vision model reads it.
                warnings = (*warnings, f"{NEEDS_VISION}:{item.media_type}")
            return ExtractionResult(status="unsupported", parser_name="ParserRouter", warnings=warnings)
        return parser.parse(item)


@dataclass(frozen=True, slots=True)
class IndexedMaterial:
    material_id: str
    version_id: str
    representation_id: str
    text: str
    segments: tuple[object, ...]


class InMemoryMaterialIndexer:
    """Minimal index adapter used for local development and tests."""
    version = "memory-index-1"

    def __init__(self) -> None:
        self.documents: dict[str, IndexedMaterial] = {}

    def index(self, *, material_id: str, version_id: str, representation_id: str,
              text: str, segments: tuple[object, ...]) -> str:
        self.documents[material_id] = IndexedMaterial(
            material_id, version_id, representation_id, text, tuple(segments))
        return "ready"

    def search(self, query: str, *, limit: int = 10) -> tuple[IndexedMaterial, ...]:
        terms = set(re.findall(r"[a-z0-9]+", query.casefold()))
        scored = []
        for doc in self.documents.values():
            doc_terms = set(re.findall(r"[a-z0-9]+", doc.text.casefold()))
            overlap = len(terms & doc_terms)
            if overlap:
                scored.append((overlap / max(1, len(terms)), doc))
        scored.sort(key=lambda pair: (-pair[0], pair[1].material_id))
        return tuple(doc for _, doc in scored[:limit])

