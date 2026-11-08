#!/usr/bin/env python3
"""Run the closed loop N times for one model and report the spread.

One run is not a measurement: model output varies. This runs the same configuration
repeatedly against the fixed custodian, scores each run against the ground truth, and
reports per-run numbers with their mean, minimum and maximum, plus how much the runs
agree with each other ("same board": the same chart nodes covered and the same key
sentences assessed). Raw model responses are dropped from the saved files by default
(they are most of the 50 MB per run); use --keep-raw to keep them.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_v3_closed_loop as loop  # noqa: E402
import score_against_truth as truth_score  # noqa: E402
import score_run  # noqa: E402

METRICS = ("node_coverage", "key_sentence_recall", "claims_off_chart_share")
RUN_METRICS = ("jobs_executed", "assessments", "nothing_extracted_share", "model_calls_accepted")


def _agreement(a: set, b: set) -> float:
    return round(len(a & b) / len(a | b), 2) if (a | b) else 1.0


def board_signature(scored: dict[str, Any]) -> dict[str, set]:
    return {
        "nodes": {nid for nid, m in scored["node_matches"].items() if m["covered"]},
        "sentences": {(r["doc"], r["node"], r["relation"]) for r in scored["key_sentence_rows"] if r["assessed"]},
        "documents": set(scored["documents_assessed"]),
    }


def summarise(per_run: list[dict[str, Any]]) -> dict[str, Any]:
    """Spread of each number across runs, and pairwise agreement between runs."""
    out: dict[str, Any] = {"runs": len(per_run), "status": [r["status"] for r in per_run]}
    for key in (*METRICS, *RUN_METRICS):
        vals = [r[key] for r in per_run if r.get(key) is not None]
        if vals:
            out[key] = {"mean": round(statistics.mean(vals), 2), "min": min(vals), "max": max(vals)}
    sigs = [r["signature"] for r in per_run]
    pairs = [(i, j) for i in range(len(sigs)) for j in range(i + 1, len(sigs))]
    for facet in ("nodes", "sentences", "documents"):
        vals = [_agreement(sigs[i][facet], sigs[j][facet]) for i, j in pairs]
        out[f"agreement_{facet}"] = round(statistics.mean(vals), 2) if vals else None
    return out


def one_run(index: int, args: argparse.Namespace, truth: dict[str, Any]) -> dict[str, Any]:
    output = args.output_prefix.parent / f"{args.output_prefix.name}_run{index}.json"
    report = loop.run(args.case, output, provider=args.provider, model_name=args.model, base_url=args.base_url,
                      max_jobs=args.max_jobs, max_rounds=args.max_rounds, num_ctx=args.num_ctx,
                      answer_reserve=args.answer_reserve, reasoning_effort=args.reasoning_effort,
                      call_timeout=args.call_timeout,
                      max_job_failures=args.max_job_failures, custodian_mode="fixed",
                      holdings_path=args.holdings, chunk_jobs=args.custodian_chunk)
    run_score = score_run.summarize(report)
    scored = truth_score.score(report, truth)
    if not args.keep_raw:
        raw = report.pop("model_raw_responses", [])
        report["model_raw_responses_dropped"] = len(raw)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return {"file": str(output), "status": run_score["status"],
            **{k: scored[k] for k in METRICS}, **{k: run_score[k] for k in RUN_METRICS},
            "documents_assessed": len(scored["documents_assessed"]),
            "critical_docs_reached": scored["critical_docs_reached"],
            "signature": board_signature(scored)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider", choices=("openrouter", "ollama_native"), default="ollama_native")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output-prefix", type=Path, required=True,
                        help="files are written as <prefix>_run1.json, <prefix>_run2.json, ...")
    parser.add_argument("--case", type=Path, default=loop.V3_ROOT / "examples" / "r3_synthetic_case.json")
    parser.add_argument("--holdings", type=Path, default=loop.DEFAULT_HOLDINGS)
    parser.add_argument("--max-jobs", type=int, default=256)
    parser.add_argument("--max-rounds", type=int, default=12)
    parser.add_argument("--max-job-failures", type=int, default=25)
    parser.add_argument("--num-ctx", type=int, default=16384)
    parser.add_argument("--answer-reserve", type=int, default=0,
                        help="tokens of the window kept free for the Specialist's answer (0: no trimming)")
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high"), default=None)
    parser.add_argument("--call-timeout", type=float, default=300, help="seconds allowed for one model call")
    parser.add_argument("--custodian-chunk", type=int, default=None)
    parser.add_argument("--keep-raw", action="store_true")
    args = parser.parse_args()
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    truth = truth_score.load_truth()
    per_run = []
    for i in range(1, args.runs + 1):
        row = one_run(i, args, truth)
        per_run.append(row)
        print(f"run {i}: {row['status']}  nodes {row['node_coverage']}  key sentences {row['key_sentence_recall']}  "
              f"docs {row['documents_assessed']}  jobs {row['jobs_executed']}", flush=True)
    summary = summarise(per_run)
    summary["model"] = args.model
    summary["per_run"] = [{k: v for k, v in r.items() if k != "signature"} for r in per_run]
    destination = args.output_prefix.parent / f"{args.output_prefix.name}_summary.json"
    destination.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_run"}, indent=2))
    print(f"summary: {destination}")


if __name__ == "__main__":
    main()
