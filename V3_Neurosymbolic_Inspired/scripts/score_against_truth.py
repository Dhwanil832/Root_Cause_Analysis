#!/usr/bin/env python3
"""Score a closed-loop run output against the human RCA chart and gold evidence map.

Inputs are the two confirmed files in ``ground_truth/``: the chart transcription
(nodes, links, open items) and the evidence map (which sentences in E01-E16 bear on
each node, plus designed traps). The run output is the JSON written by
``run_v3_closed_loop.py``.

What it reports, and what it does not claim:
- **node coverage** compares each chart node with the run's claims by word overlap.
  That is a crude match, so every match is listed with its score for you to audit;
  a node can be matched wrongly or missed. Tune ``--threshold`` and look at the list.
- **key sentences** says whether the sentences the evidence map marks as important
  were ever assessed, and whether the stance the run gave them is sensible
  (a sentence the map marks "insufficient" must not be called supporting or
  contradicting).
- **traps** checks the packet's designed mistakes (see the evidence map).

These are workflow measures on a synthetic packet. They do not say the incident
cause is right.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TRUTH_DIR = ROOT / "ground_truth"

STOP = frozenset("""a an and are as at be been being but by for from had has have in into is it its of on or
that the their there these this those to was were which with not no than then so such also during
after before while when where who will would could should may might can does did done""".split())
KEY_RELATIONS = {"supports", "insufficient", "conditional"}
CRITICAL_DOCS = ("E03", "E08", "E10", "E11")


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def tokens(text: str) -> frozenset[str]:
    return frozenset(_stem(w) for w in re.findall(r"[a-z0-9]+", str(text).lower()) if w not in STOP and len(w) > 1)


def match_score(node_text: str, claim_text: str) -> tuple[float, int]:
    """Share of the node's content words found in the claim, and how many were shared."""
    node, claim = tokens(node_text), tokens(claim_text)
    if not node:
        return 0.0, 0
    shared = len(node & claim)
    return shared / len(node), shared


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def sentence_matches(quote: str, seen: str) -> bool:
    a, b = normalise(quote), normalise(seen)
    if len(a) < 20 or len(b) < 20:
        return a == b and bool(a)
    return a in b or b in a


def load_truth(truth_dir: Path = TRUTH_DIR) -> dict[str, Any]:
    chart = json.loads((truth_dir / "r3_human_rca_chart.json").read_text(encoding="utf-8"))
    evidence = json.loads((truth_dir / "evidence_map_draft.json").read_text(encoding="utf-8"))
    return {"chart": chart, "evidence": evidence}


def _doc_id(title: Any) -> str:
    return str(title or "").split(".")[0]


def _effect(row: dict[str, Any]) -> str:
    return str(row.get("effect", "")).rsplit(".", 1)[-1].lower()


def _node_ids(text: str) -> list[str]:
    return re.findall(r"G\d+", text)


def score(report: dict[str, Any], truth: dict[str, Any], *, threshold: float = 0.5,
          min_shared: int = 2) -> dict[str, Any]:
    board = report.get("board", {})
    claims = board.get("claims", [])
    assessments = board.get("assessments", [])
    doc_of = {m.get("material_id"): _doc_id(m.get("title")) for m in board.get("materials", [])}
    nodes = truth["chart"]["nodes"]
    # The reported event is the chart's focal point; it must not stand in for a cause.
    causes = [c for c in claims if c.get("parent_claim_ids")]

    # --- node coverage
    matches = {}
    for node in nodes:
        best = (0.0, 0, None)
        for claim in (claims if node.get("focal") else causes):
            s, shared = match_score(node["text"], claim.get("text", ""))
            if (s, shared) > best[:2]:
                best = (s, shared, claim.get("claim_id"))
        covered = best[0] >= threshold and best[1] >= min_shared
        matches[node["id"]] = {"covered": covered, "claim_id": best[2] if covered else None,
                               "best_score": round(best[0], 2)}
    chart_nodes = [n for n in nodes if not n.get("focal")]
    covered = [n["id"] for n in chart_nodes if matches[n["id"]]["covered"]]
    matched_claims = {matches[i]["claim_id"] for i in covered}
    off_chart = [c.get("claim_id") for c in causes
                 if c.get("claim_id") not in matched_claims
                 and not any(match_score(n["text"], c.get("text", ""))[0] >= threshold
                             and match_score(n["text"], c.get("text", ""))[1] >= min_shared for n in nodes)]

    # --- key sentences
    by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in assessments:
        by_doc[doc_of.get(a.get("material_id"), "?")].append(a)
    key_rows, looked, supports_ok, overclaimed = [], 0, 0, []
    expected_supports = 0
    for node, entries in truth["evidence"]["node_evidence"].items():
        for e in entries:
            if e["relation"] not in KEY_RELATIONS or " | " in e["quote"]:
                continue
            rows = [a for a in by_doc.get(e["doc"], []) if sentence_matches(e["quote"], a.get("exact_text", ""))]
            effects = sorted({_effect(a) for a in rows})
            seen = bool(rows)
            looked += seen
            if e["relation"] == "supports":
                expected_supports += 1
                supports_ok += "supports" in effects
            if e["relation"] == "insufficient" and ({"supports", "contradicts"} & set(effects)):
                overclaimed.append({"doc": e["doc"], "quote": e["quote"][:90], "effects": effects})
            key_rows.append({"node": node[:30], "doc": e["doc"], "relation": e["relation"],
                             "assessed": seen, "effects": effects})
    key_total = len(key_rows)

    # --- nodes the packet cannot evidence must not be filled in
    no_evidence = sorted({i for s in truth["evidence"].get("nodes_with_no_evidence_in_packet", []) for i in _node_ids(s)})
    node_text = {n["id"]: n["text"] for n in nodes}
    filled = []
    for nid in no_evidence:
        cid = matches.get(nid, {}).get("claim_id")
        if cid and any(a.get("claim_id") == cid and _effect(a) == "supports" for a in assessments):
            filled.append(nid)

    # --- traps
    def claims_for(node_id: str) -> set[str]:
        return {c.get("claim_id") for c in causes
                if match_score(node_text[node_id], c.get("text", ""))[0] >= threshold
                and match_score(node_text[node_id], c.get("text", ""))[1] >= min_shared}
    g13 = claims_for("G13")
    e16_support = sorted({a["claim_id"] for a in by_doc.get("E16", []) if _effect(a) == "supports"})
    e08_support = {a["claim_id"] for a in by_doc.get("E08", []) if _effect(a) == "supports"}
    g19 = claims_for("G19")
    e13_on_original = sorted({a["claim_id"] for a in by_doc.get("E13", [])
                              if _effect(a) == "supports" and a["claim_id"] in g19})
    docs_assessed = sorted(d for d in by_doc if d.startswith("E"))
    all_docs = sorted(d for d in doc_of.values() if d.startswith("E"))
    return {
        "nodes_total": len(chart_nodes), "nodes_covered": len(covered),
        "node_coverage": round(len(covered) / len(chart_nodes), 2) if chart_nodes else None,
        "node_matches": {k: v for k, v in matches.items() if k != "G00"},
        "claims_total": len(causes), "claims_off_chart": len(off_chart),
        "claims_off_chart_share": round(len(off_chart) / len(causes), 2) if causes else None,
        "key_sentences_total": key_total, "key_sentences_assessed": looked,
        "key_sentence_recall": round(looked / key_total, 2) if key_total else None,
        "expected_supports": expected_supports, "supports_found": supports_ok,
        "insufficient_overclaimed": overclaimed,
        "unresolved_nodes_wrongly_supported": filled,
        "documents_registered": len(all_docs), "documents_assessed": docs_assessed,
        "critical_docs_reached": {d: d in by_doc for d in CRITICAL_DOCS},
        "traps": {
            "E16_supports_valve_claim": bool(set(e16_support) & g13),
            "E16_double_counted_with_E08": bool(set(e16_support) & e08_support & g13),
            "E13_supports_original_keeper_claim": e13_on_original,
        },
        "key_sentence_rows": key_rows,
    }


def render(name: str, s: dict[str, Any]) -> str:
    lines = [f"== {name}",
             f"chart nodes covered     {s['nodes_covered']}/{s['nodes_total']}  ({s['node_coverage']})",
             f"claims off the chart    {s['claims_off_chart']}/{s['claims_total']}  ({s['claims_off_chart_share']})",
             f"key sentences assessed  {s['key_sentences_assessed']}/{s['key_sentences_total']}  ({s['key_sentence_recall']})",
             f"expected 'supports' found {s['supports_found']}/{s['expected_supports']}",
             f"insufficient overclaimed  {len(s['insufficient_overclaimed'])}",
             f"unresolved nodes wrongly supported  {s['unresolved_nodes_wrongly_supported'] or 'none'}",
             f"documents assessed      {len(s['documents_assessed'])}/{s['documents_registered']}  {s['documents_assessed']}",
             f"critical docs reached   {s['critical_docs_reached']}",
             f"traps                   {s['traps']}"]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("outputs", nargs="+", type=Path)
    parser.add_argument("--truth-dir", type=Path, default=TRUTH_DIR)
    parser.add_argument("--threshold", type=float, default=0.5, help="share of a chart node's words a claim must contain")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--matches", action="store_true", help="list every node-to-claim match so it can be audited")
    args = parser.parse_args()
    truth = load_truth(args.truth_dir)
    results = {p.stem: score(json.loads(p.read_text(encoding="utf-8")), truth, threshold=args.threshold)
               for p in args.outputs}
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return
    for name, s in results.items():
        print(render(name, s))
        if args.matches:
            for nid, m in s["node_matches"].items():
                print(f"   {nid}: {'covered by ' + str(m['claim_id']) if m['covered'] else 'not covered'} (best {m['best_score']})")


if __name__ == "__main__":
    main()
