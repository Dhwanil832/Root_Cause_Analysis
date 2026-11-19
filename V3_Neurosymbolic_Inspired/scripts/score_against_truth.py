#!/usr/bin/env python3
"""Score a closed-loop run output against the human RCA chart and gold evidence map.

Inputs are the two confirmed files in ``ground_truth/``: the chart transcription
(nodes, links, open items) and the evidence map (which sentences in E01-E16 bear on
each node, plus designed traps). The run output is the JSON written by
``run_v3_closed_loop.py``.

What it reports, and what it does not claim:
- **node coverage** says which chart nodes the run's claims match. A claim whose text
  has a label in ``claim_node_labels.json`` (human) or ``claim_node_labels_judge.json``
  (judge model) uses it; human labels win. Any other claim falls back to word overlap,
  which is crude and misses most matches. The report says how many claims each way
  matched. Tune ``--threshold`` for the word overlap and look at the list.
- **key sentences** says whether the sentences the evidence map marks as important
  were ever assessed, and whether the stance the run gave them is sensible
  (a sentence the map marks "insufficient" must not be called supporting or
  contradicting). A key "supports" sentence counts as found only when it supports a
  claim that matches that sentence's chart node; support on any other claim is listed.
- **off-chart claims** are not failures; each is reported as backed by a supporting
  assessment, citing a document only, or with no source.
- **chart edges** checks each "effect caused by cause" pair of the chart against the
  board's links between matching claims: directly, through up to two other claims, or
  the wrong way round. It depends on node matching, so it is as crude as that is.
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


LABEL_FILES = (("human", "claim_node_labels.json"), ("judge", "claim_node_labels_judge.json"))
MATCHING_FITS = {"same", "part"}


def load_truth(truth_dir: Path = TRUTH_DIR) -> dict[str, Any]:
    chart = json.loads((truth_dir / "r3_human_rca_chart.json").read_text(encoding="utf-8"))
    evidence = json.loads((truth_dir / "evidence_map_draft.json").read_text(encoding="utf-8"))
    # Claim-to-node labels by claim text. Human labels win over the judge model's.
    labels: dict[str, dict[str, Any]] = {}
    for source, name in reversed(LABEL_FILES):
        path = truth_dir / name
        if path.exists():
            for row in json.loads(path.read_text(encoding="utf-8"))["labels"]:
                labels[normalise(row["claim_text"])] = {"source": source, "nodes": row["nodes"]}
    return {"chart": chart, "evidence": evidence, "labels": labels}


def label_for(truth: dict[str, Any], claim_text: str) -> dict[str, Any] | None:
    return truth.get("labels", {}).get(normalise(claim_text))


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

    node_text = {n["id"]: n["text"] for n in nodes}
    focal_ids = {n["id"] for n in nodes if n.get("focal")}

    # --- which claim matches which node: a label if the claim text has one, else word overlap
    def word_match(node_id: str, claim: dict[str, Any]) -> bool:
        s, shared = match_score(node_text[node_id], claim.get("text", ""))
        return s >= threshold and shared >= min_shared

    claim_nodes: dict[str, dict[str, str]] = {}  # claim_id -> {node_id: fit}
    match_source = defaultdict(int)
    unlabelled: list[str] = []
    for c in causes:
        label = label_for(truth, c.get("text", ""))
        if label is not None:
            claim_nodes[c.get("claim_id")] = {n["id"]: n["fit"] for n in label["nodes"]}
            match_source[label["source"]] += 1
        else:
            claim_nodes[c.get("claim_id")] = {nid: "word_match" for nid in node_text
                                              if nid not in focal_ids and word_match(nid, c)}
            match_source["word_overlap"] += 1
            unlabelled.append(c.get("text", ""))

    def claims_for(node_id: str) -> set[str]:
        """Every claim that matches the node, not only the best one; the focal node takes the reported event."""
        if node_id in focal_ids:
            return {c.get("claim_id") for c in claims if not c.get("parent_claim_ids")}
        return {cid for cid, fits in claim_nodes.items() if fits.get(node_id) in (*MATCHING_FITS, "word_match")}

    def claims_against(node_id: str) -> set[str]:
        return {cid for cid, fits in claim_nodes.items() if fits.get(node_id) == "opposite"}

    # --- node coverage
    matches = {}
    for node in nodes:
        best = (0.0, 0, None)
        for claim in (claims if node.get("focal") else causes):
            s, shared = match_score(node["text"], claim.get("text", ""))
            if (s, shared) > best[:2]:
                best = (s, shared, claim.get("claim_id"))
        matching = sorted(claims_for(node["id"]))
        matches[node["id"]] = {"covered": bool(matching), "claim_id": matching[0] if matching else None,
                               "claim_ids": matching, "best_score": round(best[0], 2)}
    chart_nodes = [n for n in nodes if not n.get("focal")]
    covered = [n["id"] for n in chart_nodes if matches[n["id"]]["covered"]]
    off_chart = [cid for cid, fits in claim_nodes.items() if not fits]

    # --- off-chart claims: is anything behind them? The board keeps only the cited
    # material IDs, not the quoted words, so a claim's own quote cannot be checked here.
    supported = {a.get("claim_id") for a in assessments if _effect(a) == "supports"}
    claim_by_id = {c.get("claim_id"): c for c in claims}
    off_chart_rows = [{"claim_id": cid, "text": str(claim_by_id[cid].get("text", ""))[:100],
                       "cites_document": bool(claim_by_id[cid].get("provenance")),
                       "has_supporting_assessment": cid in supported} for cid in off_chart]

    # --- key sentences
    by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in assessments:
        by_doc[doc_of.get(a.get("material_id"), "?")].append(a)
    key_rows, looked, supports_ok, supports_any, overclaimed = [], 0, 0, 0, []
    supports_elsewhere, supports_denying = [], []
    expected_supports = 0
    for node, entries in truth["evidence"]["node_evidence"].items():
        # A key such as "G06 ...; G08 ..." names several nodes; a claim matching any of them counts.
        right_claims = set().union(*(claims_for(nid) for nid in _node_ids(node)))
        denying_claims = set().union(*(claims_against(nid) for nid in _node_ids(node)))
        for e in entries:
            if e["relation"] not in KEY_RELATIONS or " | " in e["quote"]:
                continue
            rows = [a for a in by_doc.get(e["doc"], []) if sentence_matches(e["quote"], a.get("exact_text", ""))]
            effects = sorted({_effect(a) for a in rows})
            seen = bool(rows)
            looked += seen
            if e["relation"] == "supports":
                expected_supports += 1
                supporting = {a.get("claim_id") for a in rows if _effect(a) == "supports"}
                supports_any += bool(supporting)
                supports_ok += bool(supporting & right_claims)
                if supporting and not supporting & right_claims:
                    supports_elsewhere.append({"node": node[:30], "doc": e["doc"], "quote": e["quote"][:90],
                                               "claims": sorted(supporting)})
                # Evidence for a node used to support a claim that denies it.
                if supporting & denying_claims:
                    supports_denying.append({"node": node[:30], "doc": e["doc"], "quote": e["quote"][:90],
                                             "claims": sorted(supporting & denying_claims)})
            if e["relation"] == "insufficient" and ({"supports", "contradicts"} & set(effects)):
                overclaimed.append({"doc": e["doc"], "quote": e["quote"][:90], "effects": effects})
            key_rows.append({"node": node[:30], "doc": e["doc"], "relation": e["relation"],
                             "assessed": seen, "effects": effects})
    key_total = len(key_rows)

    # --- nodes the packet cannot evidence must not be filled in
    no_evidence = sorted({i for s in truth["evidence"].get("nodes_with_no_evidence_in_packet", []) for i in _node_ids(s)})
    filled = []
    for nid in no_evidence:
        cid = matches.get(nid, {}).get("claim_id")
        if cid and any(a.get("claim_id") == cid and _effect(a) == "supports" for a in assessments):
            filled.append(nid)

    # --- cause links: each chart pair "effect caused by cause" against the board's links
    links = board.get("causal_links", [])
    successors: dict[str, set[str]] = defaultdict(set)
    for link in links:
        for source in link.get("source_claim_ids", ()):
            successors[source].add(link.get("target_claim_id"))

    def reaches(starts: set[str], goals: set[str], max_links: int) -> bool:
        frontier, seen = set(starts), set(starts)
        for _ in range(max_links):
            frontier = {nxt for cid in frontier for nxt in successors.get(cid, ())} - seen
            if frontier & goals:
                return True
            seen |= frontier
        return False

    edge_rows = []
    for effect, causes_of in truth["chart"].get("edges_effect_caused_by", []):
        for cause in causes_of:
            cause_claims, effect_claims = claims_for(cause), claims_for(effect)
            edge_rows.append({
                "cause": cause, "effect": effect, "both_ends_on_board": bool(cause_claims and effect_claims),
                "direct_link": reaches(cause_claims, effect_claims, 1),
                "via_other_claims": reaches(cause_claims, effect_claims, 3),
                "reversed_link": reaches(effect_claims, cause_claims, 1),
            })
    link_status = defaultdict(int)
    for link in links:
        link_status[str(link.get("status", "?"))] += 1

    # --- traps
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
        "off_chart_with_support": sum(r["has_supporting_assessment"] for r in off_chart_rows),
        "off_chart_citing_only": sum(r["cites_document"] and not r["has_supporting_assessment"]
                                     for r in off_chart_rows),
        "off_chart_no_source": sum(not r["cites_document"] and not r["has_supporting_assessment"]
                                   for r in off_chart_rows),
        "off_chart_rows": off_chart_rows,
        "key_sentences_total": key_total, "key_sentences_assessed": looked,
        "key_sentence_recall": round(looked / key_total, 2) if key_total else None,
        "expected_supports": expected_supports, "supports_found": supports_ok,
        "supports_found_any_claim": supports_any, "supports_on_other_claims": supports_elsewhere,
        "supports_on_denying_claims": supports_denying,
        "claim_matching": dict(match_source), "unlabelled_claims": unlabelled,
        "edges_total": len(edge_rows),
        "edges_both_ends_on_board": sum(r["both_ends_on_board"] for r in edge_rows),
        "edges_linked_directly": sum(r["direct_link"] for r in edge_rows),
        "edges_linked_via_other_claims": sum(r["via_other_claims"] for r in edge_rows),
        "edges_linked_reversed": sum(r["reversed_link"] for r in edge_rows),
        "edge_rows": edge_rows, "links_total": len(links), "links_by_status": dict(link_status),
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
             f"claims off the chart    {s['claims_off_chart']}/{s['claims_total']}  ({s['claims_off_chart_share']})"
             f"  with a support {s['off_chart_with_support']}, citing a document only {s['off_chart_citing_only']},"
             f" no source {s['off_chart_no_source']}",
             f"key sentences assessed  {s['key_sentences_assessed']}/{s['key_sentences_total']}  ({s['key_sentence_recall']})",
             f"expected 'supports' found on the right claim {s['supports_found']}/{s['expected_supports']}"
             f"  (on any claim {s['supports_found_any_claim']}, on a claim denying the node"
             f" {len(s['supports_on_denying_claims'])})",
             f"claims matched to nodes by  {s['claim_matching'] or 'none'}",
             f"chart edges             {s['edges_total']}: both ends on board {s['edges_both_ends_on_board']},"
             f" linked directly {s['edges_linked_directly']}, via other claims {s['edges_linked_via_other_claims']},"
             f" reversed {s['edges_linked_reversed']}",
             f"board links by status   {s['links_by_status'] or 'none'}",
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
    parser.add_argument("--unlabelled", action="store_true",
                        help="list claims with no label (scored by word overlap) so they can be labelled")
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
        if args.unlabelled:
            for text in s["unlabelled_claims"]:
                print(f"   unlabelled: {text}")


if __name__ == "__main__":
    main()
