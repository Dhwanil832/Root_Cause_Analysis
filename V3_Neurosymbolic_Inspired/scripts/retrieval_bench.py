#!/usr/bin/env python3
"""Offline retrieval benchmark against the confirmed evidence map.

Each ground-truth node that has evidence in the packet becomes a query (its chart
text, with and without request-style padding). The sentences the evidence map quotes
for that node are the gold passages. A retriever is scored on how many gold passages
it returns in its top K (recall) and how much of what it returns is gold or at least
from a gold document (precision); passages that match only on filler words count as
noise. No model is used, so this is fast and repeatable.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

V3 = Path(__file__).resolve().parents[1]
ROOT = V3.parent
if str(V3) not in sys.path:
    sys.path.insert(0, str(V3))

from ewv3 import InMemoryRetriever  # noqa: E402
from ewv3.retrieval import default_retriever  # noqa: E402
from ewv3.contracts import SourceUnit  # noqa: E402

CASE = V3 / "examples" / "r3_synthetic_case.json"
EVIDENCE_MAP = ROOT / "ground_truth" / "evidence_map_draft.json"
CHART = ROOT / "ground_truth" / "r3_human_rca_chart.json"
PADDINGS = ("{}", "Please provide the records that show: {}", "Was it the case that {} during the outage?")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def load_sources() -> tuple[SourceUnit, ...]:
    case = json.loads(CASE.read_text(encoding="utf-8"))
    items = list(case["initial_items"]) + [i for s in case["later_submissions"] for i in s["items"]]
    return tuple(SourceUnit(i["item_id"], "v1", f"{i['item_id']}:r", i["item_id"],
                            (CASE.parent / i["path"]).resolve().read_text(encoding="utf-8")) for i in items)


def load_queries() -> list[dict[str, Any]]:
    """One entry per node with packet evidence: node id, chart text, gold (doc, sentence) pairs."""
    chart = {n["id"]: n["text"] for n in json.loads(CHART.read_text(encoding="utf-8"))["nodes"]}
    evidence = json.loads(EVIDENCE_MAP.read_text(encoding="utf-8"))["node_evidence"]
    out = []
    for label, rows in evidence.items():
        node = label.split()[0]
        out.append({"node": node, "text": chart.get(node, label),
                    "gold": [(r["doc"], _norm(r["quote"])) for r in rows]})
    return out


def is_gold(hit, gold: list[tuple[str, str]]) -> bool:
    passage = _norm(hit.excerpt)
    return any(hit.source_id == doc and passage and (passage in quote or quote in passage) for doc, quote in gold)


def evaluate(retriever, sources, queries, *, channel: str = "lexical", k: int = 8) -> dict[str, Any]:
    rows, recalls, precisions, doc_precisions = [], [], [], []
    for q in queries:
        for pad in PADDINGS:
            query = pad.format(q["text"])
            hits = retriever.search(query, channel=channel, sources=sources, limit=k)
            gold_found = {g for g in q["gold"] if any(is_gold(h, [g]) for h in hits)}
            gold_docs = {d for d, _ in q["gold"]}
            hit_gold = sum(is_gold(h, q["gold"]) for h in hits)
            hit_doc = sum(h.source_id in gold_docs for h in hits)
            recalls.append(len(gold_found) / len(q["gold"]))
            precisions.append(hit_gold / len(hits) if hits else 0.0)
            doc_precisions.append(hit_doc / len(hits) if hits else 0.0)
            rows.append({"node": q["node"], "query": query, "returned": len(hits), "gold_found": len(gold_found),
                         "gold_total": len(q["gold"]), "passage_precision": round(precisions[-1], 2)})
    mean = lambda xs: round(sum(xs) / len(xs), 3) if xs else 0.0
    return {"recall_at_k": mean(recalls), "passage_precision": mean(precisions),
            "gold_document_precision": mean(doc_precisions),
            "mean_returned": mean([r["returned"] for r in rows]), "k": k, "rows": rows}


def grade_with_model(model: str, query: str, hits, *, base_url: str = "http://localhost:11434",
                     num_ctx: int = 16384) -> dict[str, tuple[int, str]]:
    """Ask a local model to grade candidates exactly as the Evidence Worker does."""
    import urllib.request
    from ewv3.prompts import GRADE_SCHEMA, GRADE_SYSTEM
    ids = {f"c{i}": h for i, h in enumerate(hits)}
    payload = {"slots": [{"slot_id": "s", "question": query, "target_claim": query, "candidates": [{
        "candidate_link_id": cid, "document": h.structural_context.get("document_title", h.source_id),
        "document_details": h.structural_context.get("document_details", []),
        "section": h.structural_context.get("section", ""),
        "passage": h.structural_context.get("readable_text", h.excerpt),
        "before": h.structural_context.get("before", ""), "after": h.structural_context.get("after", ""),
    } for cid, h in ids.items()]}]}
    body = json.dumps({"model": model, "stream": False, "format": GRADE_SCHEMA,
                       "options": {"temperature": 0, "num_ctx": num_ctx},
                       "messages": [{"role": "system", "content": GRADE_SYSTEM},
                                    {"role": "user", "content": json.dumps(payload)}]}).encode()
    request = urllib.request.Request(f"{base_url}/api/chat", body, {"Content-Type": "application/json"})
    reply = json.loads(urllib.request.urlopen(request, timeout=900).read())["message"]["content"]
    out = {}
    for row in json.loads(reply).get("grades", []):
        if row.get("candidate_link_id") in ids:
            out[row["candidate_link_id"]] = (row["grade"], row.get("role", ""))
    return {cid: out.get(cid, (0, "ungraded")) for cid in ids}, ids


def evaluate_graded(retriever, sources, queries, *, model: str, channel: str = "lexical", pool: int = 16,
                    min_grade: int = 2) -> dict[str, Any]:
    import time
    started, recalls, precisions, kept_counts, pool_recalls = time.time(), [], [], [], []
    for q in queries:
        hits = retriever.search(q["text"], channel=channel, sources=sources, limit=pool)
        grades, ids = grade_with_model(model, q["text"], hits)
        kept = [ids[c] for c, (g, _r) in grades.items() if g >= min_grade]
        pool_recalls.append(sum(any(is_gold(h, [g]) for h in hits) for g in q["gold"]) / len(q["gold"]))
        recalls.append(sum(any(is_gold(h, [g]) for h in kept) for g in q["gold"]) / len(q["gold"]))
        precisions.append(sum(is_gold(h, q["gold"]) for h in kept) / len(kept) if kept else 0.0)
        kept_counts.append(len(kept))
        print(f"  {q['node']}: pool {len(hits)} kept {len(kept)} recall {recalls[-1]:.2f} precision {precisions[-1]:.2f}",
              flush=True)
    mean = lambda xs: round(sum(xs) / len(xs), 3) if xs else 0.0
    return {"model": model, "pool": pool, "pool_recall": mean(pool_recalls), "kept_recall": mean(recalls),
            "kept_precision": mean(precisions), "mean_kept": mean(kept_counts),
            "seconds": round(time.time() - started)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--channel", default="lexical")
    parser.add_argument("-k", type=int, default=8)
    parser.add_argument("--rows", action="store_true", help="print the per-query rows")
    parser.add_argument("--grade-model", help="also grade the candidates with this local Ollama model")
    parser.add_argument("--default", action="store_true", help="use the Evidence Worker's default retriever")
    args = parser.parse_args()
    retriever = default_retriever() if args.default or args.grade_model else InMemoryRetriever()
    if args.grade_model:
        print(json.dumps(evaluate_graded(retriever, load_sources(), load_queries(), model=args.grade_model,
                                         channel=args.channel, pool=args.k), indent=2))
        return
    result = evaluate(retriever, load_sources(), load_queries(), channel=args.channel, k=args.k)
    rows = result.pop("rows")
    print(json.dumps(result, indent=2))
    if args.rows:
        for r in rows:
            print(r)


if __name__ == "__main__":
    main()
