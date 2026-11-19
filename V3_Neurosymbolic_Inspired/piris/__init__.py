"""PIRIS: Provenance-Preserving Intake, Registration, Indexing, and Signaling."""
from .components import InMemoryMaterialIndexer, ParserRouter, TextContentParser
from .contracts import (
    ExtractedSegment, ExtractionResult, IncomingItem, IntakeAssignment,
    IntakeResult, IntakeState, ItemSuggestion, LinkBasis, LinkRecord,
    MaterialArrivalEvent, MaterialProcessingUpdate, MaterialRecord,
    RequestReference, SourceLocation,
)
from .engine import IntakeEngine
from .origins import OriginMap, OriginStatement, case_origins, resolve_origins
from .proposal import AskIntakeInterpreter
from .store import InMemoryIntakeStore

__all__ = [
    "AskIntakeInterpreter", "ExtractedSegment", "ExtractionResult",
    "IncomingItem", "InMemoryIntakeStore", "InMemoryMaterialIndexer",
    "IntakeAssignment", "IntakeEngine", "IntakeResult", "IntakeState",
    "ItemSuggestion", "LinkBasis", "LinkRecord", "MaterialArrivalEvent",
    "MaterialRecord", "OriginMap", "OriginStatement", "ParserRouter", "RequestReference", "SourceLocation",
    "MaterialProcessingUpdate", "TextContentParser", "case_origins", "resolve_origins",
]

