"""Deterministic structure for text documents: the same reading for every model.

A document is split into typed passages with exact offsets into the original text:
title and section headings, a leading details block ("Record owner: ..."), notices,
sentences, and table rows. A table row keeps its header, so "13:02:58 | 100 | 289 | 190"
can be read as "Time 13:02:58, Yoke marker y 289, ...". The original text is never
rewritten: every passage is an exact span, so quotes and offsets stay verifiable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

VERSION = "docstruct-text-1"

# Passage kinds that are evidence. Headings and details are context for them;
# notices and table header/rule lines are neither.
EVIDENCE_KINDS = frozenset({"sentence", "table_row"})

_DETAIL = re.compile(r"^[A-Z][A-Za-z /-]{1,40}:\s+\S")
_NOTICE = re.compile(r"^\*\*.*\*\*$|^>")
_RULE = re.compile(r"^\|?\s*:?-{3,}")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


@dataclass(frozen=True, slots=True)
class Passage:
    index: int
    kind: str          # title | heading | detail | notice | sentence | table_header | table_row
    start: int
    end: int
    text: str
    section: str = ""
    table_header: tuple[str, ...] = ()
    cells: tuple[str, ...] = ()

    def readable(self) -> str:
        """Table rows written out with their column names; other passages unchanged."""
        if self.kind == "table_row" and self.table_header:
            return "; ".join(f"{h}: {c}" for h, c in zip(self.table_header, self.cells))
        return self.text


@dataclass(frozen=True, slots=True)
class DocumentStructure:
    title: str
    details: tuple[str, ...]
    passages: tuple[Passage, ...]
    version: str = VERSION
    sections: tuple[str, ...] = field(default=())

    def evidence(self) -> tuple[Passage, ...]:
        return tuple(p for p in self.passages if p.kind in EVIDENCE_KINDS)

    def neighbours(self, passage: Passage) -> tuple[Passage | None, Passage | None]:
        """The evidence passages just before and after, within the same section."""
        same = [p for p in self.passages if p.section == passage.section and p.kind in EVIDENCE_KINDS]
        at = next((i for i, p in enumerate(same) if p.index == passage.index), None)
        if at is None:
            return None, None
        return (same[at - 1] if at > 0 else None, same[at + 1] if at + 1 < len(same) else None)


def _cells(line: str) -> tuple[str, ...]:
    return tuple(c.strip() for c in line.strip().strip("|").split("|"))


def _lines(text: str):
    position = 0
    for raw in text.splitlines(keepends=True):
        body = raw.rstrip("\r\n")
        left = len(body) - len(body.lstrip())
        stripped = body.strip()
        if stripped:
            yield position + left, position + left + len(stripped), stripped
        position += len(raw)


def parse(text: str) -> DocumentStructure:
    passages: list[Passage] = []
    title, section, details, sections = "", "", [], []
    header: tuple[str, ...] = ()
    seen_section = False
    lines = list(_lines(text))

    def add(kind, start, end, body, **kw):
        passages.append(Passage(len(passages), kind, start, end, body, section, **kw))

    for i, (start, end, line) in enumerate(lines):
        is_pipe = line.count("|") >= 1 and not line.startswith("#")
        prev_pipe = i > 0 and lines[i - 1][2].count("|") >= 1 and not lines[i - 1][2].startswith("#")
        next_pipe = i + 1 < len(lines) and lines[i + 1][2].count("|") >= 1 and not lines[i + 1][2].startswith("#")
        if not is_pipe:
            header = ()
        if line.startswith("#"):
            name = line.lstrip("#").strip()
            if line.startswith("##"):
                section, seen_section = name, True
                sections.append(name)
            elif not title:
                title = name
            add("title" if not line.startswith("##") else "heading", start, end, line)
        elif _NOTICE.match(line):
            add("notice", start, end, line)
        elif is_pipe and (prev_pipe or next_pipe) and seen_section:
            if _RULE.match(line):
                add("table_rule", start, end, line)
            elif not header:
                header = _cells(line)
                add("table_header", start, end, line, cells=header)
            else:
                add("table_row", start, end, line, table_header=header, cells=_cells(line))
        elif not seen_section and (_DETAIL.match(line) or (is_pipe and ":" in line)):
            details.append(line)
            add("detail", start, end, line)
        else:
            cursor = 0
            for piece in _SENTENCE_END.split(line):
                at = line.find(piece, cursor)
                cursor = at + len(piece)
                piece_end = start + at + len(piece.rstrip())
                if piece.strip():
                    add("sentence", start + at, piece_end, piece.strip())
    return DocumentStructure(title, tuple(details), tuple(passages), sections=tuple(sections))
