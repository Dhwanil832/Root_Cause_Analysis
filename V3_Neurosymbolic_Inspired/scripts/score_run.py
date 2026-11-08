#!/usr/bin/env python3
"""Score closed-loop run outputs so a change can be judged by numbers.

Reads one or more files written by run_v3_closed_loop.py and prints, per run:
reliability (how it ended, what was rejected), efficiency (jobs, model calls,
repeat work), evidence signals (assessment mix, share with nothing extracted),
and how far the closed loop got. With several files it adds a completion tally.

These are workflow signals, not a verdict on the incident: the fixtures are
synthetic, and `neutral` or "nothing extracted" can be correct. The share with
nothing extracted is a proxy for retrieval noise, not a measure of truth.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

EXECUTED_STATES = {"returned", "complete", "failed", "awaiting_assessor",
                   "needs_revision", "waiting_external", "running"}
NO_STATEMENT = "No relevant source statement"


def _state(row: dict[str, Any]) -> str:
    return str(row.get("state", "")).rsplit(".", 1)[-1].lower()


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    meta = report.get("run_metadata", {})
    board = report.get("board", {})
    work = report.get("work", [])
    raw = report.get("model_raw_responses", [])
    sim = report.get("closed_loop_simulation", {})
    assessments = board.get("assessments", [])
    failure = meta.get("failure") or {}
    job_failures = meta.get("job_failures", report.get("job_failures", []))

    by_role_state = Counter((str(w.get("role")), _state(w)) for w in work)
    assessor_done = sum(n for (role, st), n in by_role_state.items()
                        if role == "assessor" and st in {"returned", "failed"})
    accepted = Counter(r["task"] for r in raw if r.get("outcome") == "accepted")
    pairs = {(a.get("claim_id"), a.get("exact_text")) for a in assessments}
    empty = sum(NO_STATEMENT in str(a.get("rationale", "")) for a in assessments)
    trace = Counter(e.get("event") for e in sim.get("outward_trace", []))
    return {
        "status": meta.get("run_status", "unknown"),
        "aborted_by": (f"{failure.get('type')}: {str(failure.get('message', ''))[:110]}" if failure else "-"),
        "job_failures": len(job_failures),
        "job_failure_kinds": dict(Counter(f"{f.get('role')}:{f.get('status')}" for f in job_failures)),
        "jobs_budget": meta.get("role_job_budget"),
        "jobs_executed": sum(n for (_r, st), n in by_role_state.items() if st in EXECUTED_STATES),
        "open_work": {role: n for (role, st), n in sorted(by_role_state.items()) if st == "queued"},
        "stale": sum(n for (_r, st), n in by_role_state.items() if st == "stale"),
        "superseded": sum(n for (_r, st), n in by_role_state.items() if st == "superseded"),
        "model_calls_accepted": sum(accepted.values()),
        "model_attempts_not_accepted": sum(r.get("outcome") != "accepted" for r in raw),
        "extractions_per_assessor_job": (round(accepted["extract_statements"] / assessor_done, 2)
                                         if assessor_done else None),
        "assessments": len(assessments),
        "distinct_claim_sentence_pairs": len(pairs),
        "repeat_factor": round(len(assessments) / len(pairs), 2) if pairs else None,
        "effects": dict(Counter(str(a.get("effect")).rsplit(".", 1)[-1] for a in assessments)),
        "nothing_extracted_share": round(empty / len(assessments), 2) if assessments else None,
        "jobs_by_role": dict(Counter(role for _id, role in meta.get("completed_role_jobs", []))),
        "materials_registered": len(board.get("materials", [])),
        "materials_assessed": len({a.get("material_id") for a in assessments}
                                  & {m.get("material_id") for m in board.get("materials", [])}),
        "claims": len(board.get("claims", [])), "causal_links": len(board.get("causal_links", [])),
        "requests": dict(Counter(_state(r) for r in board.get("requests", []))),
        "open_needs": sum(_state(n) == "open" for n in board.get("needs", [])),
        "requests_dispatched": len(sim.get("dispatched_request_ids", [])),
        "requests_responded": len(sim.get("responded_request_ids", [])),
        "fixture_waves_arrived": trace.get("fixture_material_arrival", 0),
        "custodian_replies": trace.get("synthetic_custodian_replied", 0),
    }


def render(named: dict[str, dict[str, Any]]) -> str:
    names = list(named)
    keys = list(next(iter(named.values())))
    width = max(len(k) for k in keys)
    cell = lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
    lines = []
    for key in keys:
        lines.append(f"{key.ljust(width)}  " + "  |  ".join(cell(named[n][key]) for n in names))
    header = " " * width + "  " + "  |  ".join(names)
    tally = Counter(s["status"] for s in named.values())
    footer = (f"\nruns: {len(named)}  " + "  ".join(f"{k}: {v}" for k, v in sorted(tally.items()))
              + f"  completion rate: {tally.get('completed', 0)}/{len(named)} clean, "
                f"{tally.get('completed_with_job_failures', 0)} with job failures")
    return "\n".join([header, *lines]) + footer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outputs", nargs="+", type=Path, help="run output JSON files")
    parser.add_argument("--json", action="store_true", help="print the numbers as JSON instead of a table")
    args = parser.parse_args()
    named = {p.stem: summarize(json.loads(p.read_text(encoding="utf-8"))) for p in args.outputs}
    print(json.dumps(named, indent=2, ensure_ascii=False) if args.json else render(named))


if __name__ == "__main__":
    main()
