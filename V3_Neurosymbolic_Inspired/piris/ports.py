"""Replaceable parser, interpretation, and indexing ports."""
from __future__ import annotations

from typing import Protocol

from .contracts import (
    ExtractionResult, IncomingItem, InterpretationRequest, ItemSuggestion,
    RequestReference,
)


class ContentParser(Protocol):
    def parse(self, item: IncomingItem) -> ExtractionResult: ...


class IntakeInterpreter(Protocol):
    """Suggests metadata and links; must not assess evidence meaning."""
    version: str

    def interpret(self, items: tuple[InterpretationRequest, ...],
                   requests: tuple[RequestReference, ...]) -> tuple[ItemSuggestion, ...]: ...


class MaterialIndexer(Protocol):
    version: str

    def index(self, *, material_id: str, version_id: str,
              representation_id: str, text: str,
              segments: tuple[object, ...]) -> str: ...


class UnsafeContentError(ValueError):
    """Raised by an injected file safety scanner for content that must be quarantined."""

