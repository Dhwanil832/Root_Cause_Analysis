#!/usr/bin/env python3
"""Label which chart node a run's claims match, using a fixed judge model.

The scorer matches claims to chart nodes by label when a claim's text has one
(``ground_truth/claim_node_labels.json``, written by people) and falls back to word
overlap otherwise, which misses most matches. This script fills the gap with a judge
model that is never the model under test, so the pipeline stays all one model while
the scoring stays independent of it.

Two modes:
- ``--validate`` asks the judge about every human-labelled claim and reports how often
  it agrees. Use the judge only if it agrees well enough; self-consistency is not
  accuracy, so the human labels are the check.
- ``--label RUN.json ...`` asks the judge about every claim in those runs that has no
  human label, and merges the answers into ``claim_node_labels_judge.json``.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

V3 = Path(__file__).resolve().parents[1]
ROOT = V3.parent
sys.path[:0] = [str(V3 / "scripts"), str(ROOT / "V1_V2_Prompt_and_Rules/source/RCA_Version_Labeled_Codebase")]
from score_against_truth import TRUTH_DIR, normalise  # noqa: E402

FITS = ("same", "part", "opposite")
SYSTEM = """You match one claim from an incident investigation against the nodes of a human root cause chart.
For each chart node the claim is about, give the fit:
- same: the claim states what the node states
- part: the claim states part of the node, or one specific instance of it
- opposite: the claim denies what the node states
Return no node when the claim is about none of them. Most claims match zero, one or two nodes.
Judge meaning, not shared words. Do not judge whether the claim is true."""


def chart_nodes(truth_dir: Path) -> list[dict[str, str]]:
    chart = json.loads((truth_dir / "r3_human_rca_chart.json").read_text(encoding="utf-8"))
    evidence = json.loads((truth_dir / "evidence_map_draft.json").read_text(encoding="utf-8"))
    # The evidence map's headings describe some nodes more fully than the chart's own text.
    notes: dict[str, list[str]] = {}
    for heading in evidence["node_evidence"]:
        for part in heading.split(";"):
            node_id = part.strip().split(" ", 1)[0]
            if node_id.startswith("G") and " " in part.strip():
                notes.setdefault(node_id, []).append(part.strip().split(" ", 1)[1])
    return [{"id": n["id"], "text": n["text"], **({"note": "; ".join(notes[n["id"]])} if n["id"] in notes else {})}
            for n in chart["nodes"] if not n.get("focal")]


def schema(node_ids: list[str]) -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": ["nodes", "reason"], "properties": {
        "nodes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["id", "fit"],
            "properties": {"id": {"enum": node_ids}, "fit": {"enum": list(FITS)}}}},
        "reason": {"type": "string"}}}


def judge(client, nodes: list[dict[str, str]], claim_text: str) -> dict[str, Any]:
    reply = client.ask("claim_node_match", SYSTEM, {"chart_nodes": nodes, "claim": claim_text})
    seen, kept = set(), []
    for row in reply["nodes"]:
        if row["id"] not in seen:
            seen.add(row["id"])
            kept.append({"id": row["id"], "fit": row["fit"]})
    return {"nodes": kept, "reason": reply["reason"]}


def matching(nodes: list[dict[str, str]]) -> set[str]:
    return {n["id"] for n in nodes if n["fit"] in ("same", "part")}


def opposing(nodes: list[dict[str, str]]) -> set[str]:
    return {n["id"] for n in nodes if n["fit"] == "opposite"}


def agreement(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare judge and human per claim; 'same' and 'part' both count as a match."""
    exact = sum(matching(r["human"]) == matching(r["judge"]) and opposing(r["human"]) == opposing(r["judge"])
                for r in rows)
    pairs_h = {(i, n) for i, r in enumerate(rows) for n in matching(r["human"])}
    pairs_j = {(i, n) for i, r in enumerate(rows) for n in matching(r["judge"])}
    both = len(pairs_h & pairs_j)
    none_h = [i for i, r in enumerate(rows) if not r["human"]]
    return {
        "claims": len(rows),
        "claims_in_full_agreement": exact,
        "full_agreement_share": round(exact / len(rows), 2) if rows else None,
        "node_matches_human": len(pairs_h), "node_matches_judge": len(pairs_j),
        "node_match_precision": round(both / len(pairs_j), 2) if pairs_j else None,
        "node_match_recall": round(both / len(pairs_h), 2) if pairs_h else None,
        "no_node_claims_judge_left_empty": sum(not matching(rows[i]["judge"]) for i in none_h),
        "no_node_claims": len(none_h),
    }


def run_claim_texts(paths: list[Path]) -> tuple[dict[str, str], set[str]]:
    texts, models = {}, set()
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        models.add(str(report.get("run_metadata", {}).get("model", "")))
        for claim in report.get("board", {}).get("claims", []):
            if claim.get("parent_claim_ids"):
                texts.setdefault(normalise(claim["text"]), claim["text"])
    return texts, models


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true", help="compare the judge with the human labels")
    mode.add_argument("--label", nargs="+", type=Path, metavar="RUN", help="label these runs' unlabelled claims")
    parser.add_argument("--model", required=True, help="judge model; must not be the model under test")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--num-ctx", type=int, default=8192)
    parser.add_argument("--think", choices=["off", "on", "low", "medium", "high"], default="off",
                        help="judge reasoning; off by default, since long reasoning can use up the answer budget")
    parser.add_argument("--truth-dir", type=Path, default=TRUTH_DIR)
    parser.add_argument("--output", type=Path, default=None, help="--validate: also save the rows here")
    args = parser.parse_args()

    from shared.llm.factory import create_model_client
    from shared.llm.client import ModelFailure
    nodes = chart_nodes(args.truth_dir)
    client = create_model_client(provider="ollama_native", model=args.model, base_url=args.base_url, timeout=600,
                                 task_schemas={"claim_node_match": schema([n["id"] for n in nodes])},
                                 num_ctx=args.num_ctx,
                                 think={"off": False, "on": True}.get(args.think, args.think))
    human = json.loads((args.truth_dir / "claim_node_labels.json").read_text(encoding="utf-8"))["labels"]

    if args.validate:
        rows = []
        rows, failed = [], []
        for row in human:
            try:
                answer = judge(client, nodes, row["claim_text"])
            except ModelFailure as exc:  # one bad answer should not lose the rest of the check
                failed.append({"claim_text": row["claim_text"], "error": str(exc)})
                print(f"  - failed: {row['claim_text'][:70]}", flush=True)
                continue
            rows.append({"claim_text": row["claim_text"], "human": row["nodes"], "judge": answer["nodes"],
                         "judge_reason": answer["reason"]})
            print(f"{len(rows):>3} human {sorted(matching(row['nodes']))} judge {sorted(matching(answer['nodes']))}"
                  f"  {row['claim_text'][:70]}", flush=True)
            result = {"judge_model": args.model, "think": args.think, "agreement": agreement(rows),
                      "failed": failed, "rows": rows}
            if args.output:
                args.output.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({**agreement(rows), "failed_claims": len(failed)}, indent=2))
        return

    texts, run_models = run_claim_texts(args.label)
    if args.model in run_models:
        parser.error(f"judge model {args.model} is the model under test in these runs; pick another")
    labelled = {normalise(r["claim_text"]) for r in human}
    out_path = args.truth_dir / "claim_node_labels_judge.json"
    existing = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {"labels": []}
    if existing.get("judge_model") not in (None, args.model):
        parser.error(f"{out_path.name} was written by {existing['judge_model']}; keep one judge per file")
    done = {normalise(r["claim_text"]) for r in existing["labels"]}
    todo = [text for key, text in texts.items() if key not in labelled and key not in done]
    for text in todo:
        answer = judge(client, nodes, text)
        existing["labels"].append({"claim_text": text, **answer})
        existing.update({"status": "Judge-model labels; human labels in claim_node_labels.json win.",
                         "judge_model": args.model, "updated": date.today().isoformat()})
        out_path.write_text(json.dumps(existing, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{len(existing['labels']):>4} {sorted(matching(answer['nodes']))}  {text[:80]}", flush=True)
    print(f"labelled {len(todo)} claims; {len(existing['labels'])} in {out_path.name}")


if __name__ == "__main__":
    main()
