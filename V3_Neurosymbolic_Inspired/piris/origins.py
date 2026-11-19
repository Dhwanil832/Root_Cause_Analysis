"""Origin records: where a document says it comes from.

A recap that says "Prepared from workshop record VAL-17" is not a second source for what
VAL-17 says. Intake records each such sentence, word for word, with the identifiers it
names. Matching an identifier to the document that carries it is done over the whole case
each time it is asked, so the answer does not depend on which document arrived first: a
recap that arrives before its original stays unresolved until the original arrives.

The map this produces is ``derived material -> original material``, the shape
``cferp.status`` takes as ``origins``. A material with no origin sentence is left out of
the map, so the status view shows that its independence is assumed, not known.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Mapping

_ORIGIN = re.compile(
    r"\b(?:prepared|compiled|transcribed|copied|summari[sz]ed|derived|reproduced|extracted|abstracted)"
    r"\b[^.\n]{0,80}?\bfrom\b|\bbased\s+on\b|^\s*source\s*:",
    re.IGNORECASE)
_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]+|$)", re.MULTILINE)
_CODE = re.compile(r"(?<![\w-])[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[A-Z0-9]*\d[A-Z0-9]*(?![\w-])")
_NAMED = re.compile(
    r"\b(?:record|report|document|sheet|log|docket|tag|form|file|note|summary)\s+"
    r"(?:no\.?\s*)?([A-Z0-9]*\d[A-Z0-9-]*)(?![\w-])", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class OriginStatement:
    material_id: str
    quote: str
    start_offset: int
    identifiers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OriginMap:
    origins: dict[str, str] = field(default_factory=dict)
    statements: tuple[OriginStatement, ...] = ()
    # (material_id, identifier) pairs that no document in the case carries yet
    unresolved: tuple[tuple[str, str], ...] = ()
    # (material_id, identifier, candidates) when more than one document carries it
    ambiguous: tuple[tuple[str, str, tuple[str, ...]], ...] = ()
    # origin sentences that name no identifier, so they cannot be matched
    unnamed: tuple[OriginStatement, ...] = ()


def identifiers_in(text: str) -> tuple[str, ...]:
    found = [m.group(0) for m in _CODE.finditer(text)] + [m.group(1) for m in _NAMED.finditer(text)]
    return tuple(dict.fromkeys(i.upper() for i in found))


def origin_statements(material_id: str, text: str) -> tuple[OriginStatement, ...]:
    """Each sentence in which the document says where it comes from, with its offset."""
    out = []
    for m in _SENTENCE.finditer(text):
        sentence = m.group(0)
        if not _ORIGIN.search(sentence):
            continue
        lead = len(sentence) - len(sentence.lstrip())
        quote = sentence.strip()
        out.append(OriginStatement(material_id, quote, m.start() + lead, identifiers_in(quote)))
    return tuple(out)


def _carries(text: str, identifier: str, skip: Iterable[OriginStatement]) -> bool:
    """True when the identifier occurs in the text outside the document's own origin sentences."""
    pattern = re.compile(r"(?<![\w-])" + re.escape(identifier) + r"(?![\w-])", re.IGNORECASE)
    spans = [(s.start_offset, s.start_offset + len(s.quote)) for s in skip]
    return any(not any(a <= m.start() < b for a, b in spans) for m in pattern.finditer(text))


def resolve_origins(texts: Mapping[str, str]) -> OriginMap:
    """Match each origin identifier to the one other document that carries it."""
    statements = {mid: origin_statements(mid, text) for mid, text in texts.items()}
    origins: dict[str, str] = {}
    unresolved, ambiguous, unnamed = [], [], []
    for mid, own in statements.items():
        for statement in own:
            if not statement.identifiers:
                unnamed.append(statement)
            for identifier in statement.identifiers:
                candidates = tuple(sorted(other for other, text in texts.items()
                                          if other != mid and _carries(text, identifier, statements[other])))
                if not candidates:
                    unresolved.append((mid, identifier))
                elif len(candidates) > 1:
                    ambiguous.append((mid, identifier, candidates))
                elif mid not in origins:
                    origins[mid] = candidates[0]
                elif origins[mid] != candidates[0]:
                    ambiguous.append((mid, identifier, tuple(sorted({origins[mid], candidates[0]}))))
    return OriginMap(origins, tuple(s for own in statements.values() for s in own),
                     tuple(unresolved), tuple(ambiguous), tuple(unnamed))


def material_text(material) -> str:
    text = material.extraction.text if material.extraction is not None else ""
    return text or material.content.decode("utf-8", errors="replace")


def case_origins(materials: Iterable) -> OriginMap:
    """Origins over a case's current materials. A version replaced by a revision is left out."""
    materials = tuple(materials)
    replaced = {m.revision_of for m in materials if m.revision_of}
    return resolve_origins({m.material_id: material_text(m) for m in materials
                            if m.material_id not in replaced})
