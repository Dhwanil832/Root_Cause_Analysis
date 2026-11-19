"""Claim and link status, worked out from the board by fixed rules (v0.5 Step 1).

The model proposes claims and judges passages; this module alone decides what a
claim's status is. It reads the board as it stands (live snapshot or saved run),
keeps nothing between calls, and gives the same answer for the same board.

A claim is a conjunction of parts. A passage can support one part and leave another
open, so a claim is ``shown`` only when every part has a support. A claim with no
listed parts is treated as one part, which is how every board before v0.5 reads.

Claim status, from current (not superseded) assessments, first rule that applies:

- ``reported``: the incident claim itself, which is taken as given.
- ``unchecked``: no assessment, or only ``not_relevant`` ones.
- ``contradicted``: some part has a ``contradicts`` and no ``supports``. One false part
  makes the whole claim false, whatever the other parts have.
- ``contested``: some part has both a ``supports`` and a ``contradicts``.
- ``shown``: every part has a ``supports``.
- ``partly shown``: some parts have a ``supports``; the rest are listed as missing.
- ``open``: checked, but only ``consistent_with``, ``insufficient``, ``weakens`` (or
  the old ``neutral``) so far.

Supports count once per original source. ``origins`` maps a material to the material
it was prepared from (a recap of a workshop record counts as that record), or to itself
when it is known to be an original. A material missing from ``origins`` counts as its
own source, and the result says the count assumes that.

A claim can name the claims it ``denies``. A passage that supports both claims of
such a pair is listed under ``denial_conflicts`` for review, since one reading is wrong.

Link status, until links can be assessed (Step 3): ``proposed``, or ``both ends shown``
when every source claim and the target are shown (the reported incident counts as
shown here).

The chain view follows links backwards from the incident claim and lists each path
with its weakest point, which is where the Lead should aim work next.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
from typing import Any

SUPPORTS, CONTRADICTS, NOT_RELEVANT = "supports", "contradicts", "not_relevant"
OPEN_EFFECTS = frozenset({"consistent_with", "insufficient", "weakens", "neutral"})
EFFECTS = frozenset({SUPPORTS, CONTRADICTS, NOT_RELEVANT, *OPEN_EFFECTS})
WHOLE = "(whole claim)"

REPORTED, UNCHECKED, CONTRADICTED, CONTESTED = "reported", "unchecked", "contradicted", "contested"
SHOWN, PARTLY_SHOWN, OPEN = "shown", "partly shown", "open"
PROPOSED, BOTH_ENDS_SHOWN = "proposed", "both ends shown"

# Lower is weaker: the chain view's weakest point is the lowest rank on a path.
RANK = {CONTRADICTED: 0, CONTESTED: 1, UNCHECKED: 2, PROPOSED: 2, OPEN: 3,
        PARTLY_SHOWN: 4, SHOWN: 5, BOTH_ENDS_SHOWN: 5, REPORTED: 6}
MAX_PATHS = 500


def _plain(obj: Any) -> dict[str, Any]:
    if isinstance(obj, Mapping):
        return dict(obj)
    if is_dataclass(obj):
        return asdict(obj)
    raise TypeError(f"cannot read board row of type {type(obj).__name__}")


def _value(v: Any) -> Any:
    return getattr(v, "value", v)  # enums from a live board, plain strings from a saved one


def _is_incident(claim: Mapping[str, Any]) -> bool:
    return _value(claim.get("kind")) == "incident_event" and _value(claim.get("incident_status")) == "reported"


def source_of(material_id: str, origins: Mapping[str, str]) -> str:
    """Follow 'prepared from' records back to the original material; stops on a loop."""
    seen = {material_id}
    while material_id in origins and origins[material_id] not in seen:
        material_id = origins[material_id]
        seen.add(material_id)
    return material_id


def _marks(assessment: Mapping[str, Any], parts: list[str]) -> dict[str, str]:
    """Effect per part. An assessment about no particular part applies its effect to them all."""
    effect = str(_value(assessment.get("effect")))
    given = assessment.get("part_effects") or {}
    part = assessment.get("part")
    if not given and part in parts:
        return {part: effect}
    if not given:
        return {p: effect for p in parts}
    return {p: str(_value(given[p])) for p in parts if p in given}


def claim_status(claim: Mapping[str, Any], assessments: Iterable[Mapping[str, Any]],
                 origins: Mapping[str, str] | None = None) -> dict[str, Any]:
    origins = origins or {}
    parts = list(claim.get("parts") or ()) or [WHOLE]
    current = [a for a in assessments if a.get("status", "current") == "current"]
    effects = Counter(str(_value(a.get("effect"))) for a in current)
    per_part = {p: {"support_sources": set(), "contradict_sources": set(), "open": 0} for p in parts}
    assumed = False
    for a in current:
        material = str(a.get("material_id", ""))
        source = source_of(material, origins)
        for part, effect in _marks(a, parts).items():
            if effect == SUPPORTS:
                per_part[part]["support_sources"].add(source)
                assumed |= material not in origins
            elif effect == CONTRADICTS:
                per_part[part]["contradict_sources"].add(source)
            elif effect in OPEN_EFFECTS:
                per_part[part]["open"] += 1

    supported = [p for p in parts if per_part[p]["support_sources"]]
    if _is_incident(claim):
        status = REPORTED
    elif not any(e != NOT_RELEVANT for e in effects.elements()):
        status = UNCHECKED
    elif any(v["contradict_sources"] and not v["support_sources"] for v in per_part.values()):
        status = CONTRADICTED
    elif any(v["contradict_sources"] and v["support_sources"] for v in per_part.values()):
        status = CONTESTED
    elif len(supported) == len(parts):
        status = SHOWN
    elif supported:
        status = PARTLY_SHOWN
    else:
        status = OPEN
    support_sources = set().union(*(v["support_sources"] for v in per_part.values()))
    return {
        "claim_id": claim.get("claim_id"), "status": status,
        "parts": [{"part": p, "support_sources": sorted(per_part[p]["support_sources"]),
                   "contradict_sources": sorted(per_part[p]["contradict_sources"]),
                   "open_assessments": per_part[p]["open"]} for p in parts],
        "missing_parts": [p for p in parts if not per_part[p]["support_sources"]] if status != REPORTED else [],
        "independent_sources": len(support_sources),
        "sources_assumed_independent": assumed,
        "assessments_by_effect": dict(effects),
        "not_relevant_assessments": effects.get(NOT_RELEVANT, 0),
    }


def link_status(link: Mapping[str, Any], claims: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    ends = [*link.get("source_claim_ids", ()), link.get("target_claim_id")]
    end_status = {c: claims.get(c, {}).get("status", UNCHECKED) for c in ends}
    shown = all(s in (SHOWN, REPORTED) for s in end_status.values())
    return {"link_id": link.get("link_id"), "status": BOTH_ENDS_SHOWN if shown else PROPOSED,
            "end_status": end_status}


def chain_view(claims: Mapping[str, Mapping[str, Any]], links: Mapping[str, Mapping[str, Any]],
               raw_links: Iterable[Mapping[str, Any]], incident_ids: list[str]) -> dict[str, Any]:
    """From each incident claim, follow links back to their source claims; one path per earliest cause."""
    into: dict[str, list[Mapping[str, Any]]] = {}
    for link in raw_links:
        into.setdefault(link.get("target_claim_id"), []).append(link)
    paths: list[dict[str, Any]] = []
    truncated = False

    def walk(claim_id: str, steps: list[tuple[str, str]], seen: set[str]) -> None:
        nonlocal truncated
        incoming = [l for l in into.get(claim_id, ()) if not set(l.get("source_claim_ids", ())) & seen]
        if not incoming:
            if steps:
                paths.append(_path(steps, claims, links))
            return
        for link in incoming:
            for source in link.get("source_claim_ids", ()):
                if source not in claims:
                    continue  # a link to a claim no longer on the board
                if len(paths) >= MAX_PATHS:
                    truncated = True
                    return
                walk(source, [*steps, ("link", link["link_id"]), ("claim", source)], seen | {source})

    for incident in incident_ids:
        walk(incident, [("claim", incident)], {incident})
    on_path = {cid for p in paths for kind, cid in p["steps"] if kind == "claim"}
    return {"paths": paths, "truncated": truncated,
            "claims_on_no_path": sorted(c for c in claims if c not in on_path)}


def _path(steps: list[tuple[str, str]], claims: Mapping[str, Mapping[str, Any]],
          links: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    def status(kind: str, item: str) -> str:
        return (claims if kind == "claim" else links)[item]["status"]
    claim_steps = [s for s in steps if s[0] == "claim"]
    weakest_claim = min(claim_steps, key=lambda s: RANK[status(*s)])
    weakest = min(steps, key=lambda s: RANK[status(*s)])
    return {"steps": [list(s) for s in steps], "root": steps[-1][1],
            "statuses": [status(*s) for s in steps],
            "weakest": {"kind": weakest[0], "id": weakest[1], "status": status(*weakest)},
            "weakest_claim": {"id": weakest_claim[1], "status": status(*weakest_claim)}}


def denial_conflicts(claims: Iterable[Mapping[str, Any]],
                     assessments: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Passages that support two claims when one says the other is false.

    One of the two readings is wrong, so each such passage is listed for review.
    """
    pairs = {tuple(sorted((c["claim_id"], d))) for c in claims for d in (c.get("denies") or ())}
    supported: dict[tuple[str, str], set[str]] = {}
    for a in assessments:
        if a.get("status", "current") == "current" and str(_value(a.get("effect"))) == SUPPORTS:
            passage = (str(a.get("material_id", "")), str(a.get("passage_id") or a.get("exact_text", "")))
            supported.setdefault(passage, set()).add(str(a.get("claim_id")))
    return [{"material_id": material, "passage_id": passage, "claims": list(pair)}
            for (material, passage), claim_ids in sorted(supported.items())
            for pair in sorted(pairs) if set(pair) <= claim_ids]


def material_origins(materials: Iterable[Any]) -> dict[str, str]:
    """Origin map from the materials' own text, by Intake's rule (``piris.origins``)."""
    from piris.origins import resolve_origins
    texts = {}
    for m in materials:
        row = _plain(m)
        if row.get("content"):
            texts[str(row["material_id"])] = str(row["content"])
    return resolve_origins(texts).origins


def board_status(board: Mapping[str, Any], origins: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Status of every claim and link on a board, plus the chain view.

    Without ``origins`` the map is worked out from the board's material text.
    """
    if origins is None:
        origins = material_origins(board.get("materials", ()))
    claims = [_plain(c) for c in board.get("claims", ())]
    links = [_plain(l) for l in board.get("causal_links", ())]
    by_claim: dict[str, list[dict[str, Any]]] = {}
    assessments = [_plain(a) for a in board.get("assessments", ())]
    for a in assessments:
        by_claim.setdefault(a.get("claim_id"), []).append(a)
    claim_rows = {c["claim_id"]: claim_status(c, by_claim.get(c["claim_id"], ()), origins) for c in claims}
    link_rows = {l["link_id"]: link_status(l, claim_rows) for l in links}
    incidents = [c["claim_id"] for c in claims if _is_incident(c)]
    return {
        "claims": claim_rows, "links": link_rows,
        "claims_by_status": dict(Counter(r["status"] for r in claim_rows.values())),
        "links_by_status": dict(Counter(r["status"] for r in link_rows.values())),
        "chains": chain_view(claim_rows, link_rows, links, incidents),
        "origins": dict(origins),
        "denial_conflicts": denial_conflicts(claims, assessments),
    }
