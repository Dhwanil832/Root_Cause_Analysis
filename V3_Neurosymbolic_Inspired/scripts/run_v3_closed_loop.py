#!/usr/bin/env python3
"""Replay the synthetic R3 case with simulated outward requests and replies.

Every outbound response is a clearly labeled scenario simulation. The simulated
custodian can select only documents already released in the current fixture
wave; selected items re-enter through PIRIS and the normal four-role loop.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

V3_ROOT = Path(__file__).resolve().parents[1]
COMBINED_ROOT = V3_ROOT.parent
LEGACY_ROOT = (COMBINED_ROOT / "V1_V2_Prompt_and_Rules" / "source" /
               "RCA_Version_Labeled_Codebase")
# V3 must come first: the legacy tree has packages with the same names (for example
# `orchestration`), and whichever is found first shadows the other.
for path in (LEGACY_ROOT, V3_ROOT):
    if str(path) in sys.path:
        sys.path.remove(str(path))
    sys.path.insert(0, str(path))

from orchestration.custodian import Custodian, RequestView  # noqa: E402
from orchestration.fixture_outward_responder import select_fixture_response  # noqa: E402
from orchestration.v3_runtime import V3CaseRuntime  # noqa: E402
from piris import IncomingItem  # noqa: E402
from cferp.contracts import RequestDisposition  # noqa: E402


DEFAULT_HOLDINGS = COMBINED_ROOT / "ground_truth" / "custodian_holdings.json"


def _read_item(row: dict[str, Any], case_dir: Path) -> dict[str, str]:
    if "path" in row:
        source = (case_dir / row["path"]).resolve()
        text = source.read_text(encoding="utf-8")
        filename = row.get("filename", source.name)
    else:
        text = str(row.get("text", ""))
        filename = str(row.get("filename", f"{row['item_id']}.txt"))
    return {"item_id": str(row["item_id"]), "text": text, "filename": filename,
            "declared_kind": str(row.get("declared_kind", "case_material"))}


def _incoming(row: dict[str, Any], *, item_id: str | None = None,
              request_id: str | None = None) -> IncomingItem:
    return IncomingItem.text(
        item_id or row["item_id"], row["text"], media_type="text/markdown",
        filename=row["filename"],
        declared_kind=("simulated_custodian_reply" if request_id else row["declared_kind"]),
        declared_request_id=request_id,
        metadata={"synthetic_fixture": True,
                  "fixture_source_item_id": row["item_id"],
                  "simulated_external_response": bool(request_id)},
    )


def _request_slots(workflow: Any, request: Any) -> list[dict[str, str]]:
    wanted = set(request.slot_ids)
    rows = []
    for need in workflow.lead.needs.values():
        for slot in need.slots:
            if slot.slot_id in wanted:
                rows.append({"slot_id": slot.slot_id, "description": slot.description})
    return rows


def _dispatch_ready(runtime: V3CaseRuntime, sent: set[str], trace: list[dict[str, Any]]) -> None:
    for request in list(runtime.workflow.lead.requests.values()):
        state = request.state
        if state not in {RequestDisposition.APPROVED, RequestDisposition.DISPATCH_FAILED}:
            continue
        if request.request_id in sent:
            continue
        if state == RequestDisposition.APPROVED:
            action = runtime.workflow.send_approved_request(request.request_id)
        else:
            action = runtime.workflow.lead.submit_dispatch(request.request_id, "send")
        updated = runtime.workflow.acknowledge_request_dispatch(action.action_id, success=True)
        sent.add(request.request_id)
        trace.append({"event": "outward_request_dispatched", "request_id": request.request_id,
                      "wording": request.wording, "request_kind": request.request_kind,
                      "state": updated.state.value})


def _answer_requests(runtime: V3CaseRuntime, model: Any, wave_items: list[dict[str, str]],
                     responded: set[str], trace: list[dict[str, Any]], *, final_wave: bool,
                     wave_id: str) -> None:
    for request in list(runtime.workflow.lead.requests.values()):
        if request.state not in {RequestDisposition.SENT, RequestDisposition.WAITING_RESPONSE,
                                 RequestDisposition.PARTIALLY_ANSWERED}:
            continue
        if request.request_id in responded:
            continue
        slots = _request_slots(runtime.workflow, request)
        choice = select_fixture_response(model, request, slots, wave_items)
        chosen = [row for row in wave_items if row["item_id"] in choice["selected_item_ids"]]
        if not chosen and not final_wave:
            continue
        if chosen:
            safe_items = tuple(_incoming(row, item_id=f"{row['item_id']}__reply__{request.request_id}",
                                         request_id=request.request_id) for row in chosen)
            runtime.submit_material(
                submission_id=f"simulated-reply:{wave_id}:{request.request_id}",
                items=safe_items, request_id=request.request_id,
                answered_slot_ids=choice["answered_slot_ids"],
                sender_id="synthetic-fixture-custodian",
            )
            trace.append({"event": "synthetic_custodian_replied", "request_id": request.request_id,
                          "source_item_ids": [row["item_id"] for row in chosen],
                          "answered_slot_ids": choice["answered_slot_ids"],
                          "status": "documents_submitted_for_normal_assessment"})
        else:
            # A bounded no-record reply is explicit and reviewable; it is not an
            # assertion about the real incident or a reason to close the need.
            note_id = f"no-record-{request.request_id}"
            note = IncomingItem.text(
                note_id,
                "Synthetic custodian response: no matching item was selected from the "
                "available synthetic fixture records for this request. This is a simulated "
                "search result, not proof that the requested record does not exist.",
                filename=f"{note_id}.md", declared_kind="simulated_no_record_reply",
                declared_request_id=request.request_id,
                metadata={"synthetic_fixture": True, "simulated_external_response": True,
                          "no_record_is_not_proof_of_absence": True},
            )
            runtime.submit_material(
                submission_id=f"simulated-no-record:{wave_id}:{request.request_id}",
                items=(note,), request_id=request.request_id,
                sender_id="synthetic-fixture-custodian",
            )
            trace.append({"event": "synthetic_custodian_no_match", "request_id": request.request_id,
                          "status": "reported_as_search_limit_not_absence"})
        responded.add(request.request_id)


def _open_requests(runtime: V3CaseRuntime, sent: set[str], responded: set[str]) -> list[RequestView]:
    """Requests that were dispatched and have not yet had a reply from the custodian."""
    views = []
    for request in runtime.workflow.lead.requests.values():
        if request.request_id not in sent or request.request_id in responded:
            continue
        slots = tuple((row["slot_id"], row["description"]) for row in _request_slots(runtime.workflow, request))
        views.append(RequestView(request.request_id,
                                 " ".join([request.wording, *(d for _s, d in slots)]), slots))
    return views


def _apply_custodian_actions(runtime: V3CaseRuntime, actions: list[dict[str, Any]],
                             rows_by_id: dict[str, dict[str, str]], responded: set[str],
                             trace: list[dict[str, Any]], clock: int, arrivals: list[int]) -> None:
    for action in actions:
        kind, rid = action["kind"], action.get("request_id")
        if kind == "documents":
            items = tuple(_incoming(rows_by_id[i], item_id=f"{i}__reply__{rid}", request_id=rid)
                          for i in action["item_ids"])
            runtime.submit_material(submission_id=f"custodian-reply:{rid}", items=items, request_id=rid,
                                    answered_slot_ids=action["answered_slot_ids"], sender_id="fixed-custodian")
            trace.append({"event": "synthetic_custodian_replied", "request_id": rid, "clock": clock,
                          "source_item_ids": action["item_ids"], "answered_slot_ids": action["answered_slot_ids"],
                          "stance": action["stance"], "status": "documents_submitted_for_normal_assessment"})
        elif kind == "statement":
            note = IncomingItem.text(
                f"statement-{rid}", action["text"], filename=f"statement-{rid}.md",
                declared_kind="simulated_custodian_statement", declared_request_id=rid,
                metadata={"synthetic_fixture": True, "simulated_external_response": True,
                          "unverified_testimony": True, "statement_id": action["statement_id"]})
            runtime.submit_material(submission_id=f"custodian-statement:{rid}", items=(note,),
                                    request_id=rid, sender_id="fixed-custodian")
            trace.append({"event": "synthetic_custodian_statement", "request_id": rid, "clock": clock,
                          "statement_id": action["statement_id"], "stance": action["stance"]})
        elif kind == "no_record":
            note = IncomingItem.text(
                f"no-record-{rid}",
                "Synthetic custodian response: no matching record is held for this request. This is a "
                "simulated search result, not proof that the requested record does not exist.",
                filename=f"no-record-{rid}.md", declared_kind="simulated_no_record_reply",
                declared_request_id=rid,
                metadata={"synthetic_fixture": True, "simulated_external_response": True,
                          "no_record_is_not_proof_of_absence": True})
            runtime.submit_material(submission_id=f"custodian-no-record:{rid}", items=(note,),
                                    request_id=rid, sender_id="fixed-custodian")
            trace.append({"event": "synthetic_custodian_no_match", "request_id": rid, "clock": clock,
                          "stance": action["stance"], "status": "reported_as_search_limit_not_absence"})
        elif kind == "unprompted":
            arrivals.append(len(arrivals) + 1)
            runtime.submit_material(submission_id=f"custodian-arrival-{arrivals[-1]}",
                                    items=tuple(_incoming(rows_by_id[i]) for i in action["item_ids"]),
                                    sender_id="synthetic-case-material-upload")
            trace.append({"event": "fixture_material_arrival", "submission_id": f"custodian-arrival-{arrivals[-1]}",
                          "item_ids": action["item_ids"], "clock": clock, "arrival_index": arrivals[-1]})
        if rid:
            responded.add(rid)


def _drive_fixed(runtime: V3CaseRuntime, custodian: Custodian, rows_by_id: dict[str, dict[str, str]],
                 sent: set[str], responded: set[str], trace: list[dict[str, Any]], *,
                 max_jobs: int, chunk: int, max_steps: int = 2000) -> list[Any]:
    """Run role jobs in small chunks and let the fixed custodian act between them.

    The custodian's clock counts completed jobs and jumps forward while the system is
    idle, so documents can arrive while work is queued, not only when it drains.
    """
    completed: list[Any] = []
    remaining, clock, arrivals = max_jobs, 0, []
    for _ in range(max_steps):
        ran = runtime.run_ready(max_jobs=min(chunk, remaining)) if remaining > 0 else []
        completed.extend(ran)
        remaining -= len(ran)
        clock += len(ran)
        _dispatch_ready(runtime, sent, trace)
        open_requests = _open_requests(runtime, sent, responded)
        actions = custodian.step(clock, open_requests)
        if actions:
            _apply_custodian_actions(runtime, actions, rows_by_id, responded, trace, clock, arrivals)
        if ran or actions:
            continue
        if remaining <= 0:
            trace.append({"event": "job_budget_exhausted", "clock": clock})
            break
        due = custodian.next_due(clock, open_requests)
        if due is None:
            break
        clock = max(clock + 1, due)               # nothing to do: time passes
    else:
        trace.append({"event": "driver_step_cap_reached", "max_steps": max_steps})
    return completed


RUN_EXIT_CODES = {"completed": 0, "failed_or_partial": 1, "completed_with_job_failures": 2}


def _run_status(failure: dict[str, Any] | None, job_failures: Any) -> str:
    """`completed` only if nothing was rejected; a contained failure is never hidden."""
    if failure:
        return "failed_or_partial"
    return "completed_with_job_failures" if job_failures else "completed"


def run(case_path: Path, output_path: Path, *, provider: str, model_name: str,
        base_url: str | None, max_jobs: int, max_rounds: int,
        num_ctx: int | None = None, answer_reserve: int = 0, reasoning_effort: str | None = None,
        call_timeout: float = 300,
        max_job_failures: int = 25, custodian_mode: str = "fixed",
        holdings_path: Path = DEFAULT_HOLDINGS, chunk_jobs: int | None = None) -> dict[str, Any]:
    case_path = case_path.resolve()
    case = json.loads(case_path.read_text(encoding="utf-8"))
    if provider == "ollama_native":
        runtime = V3CaseRuntime.from_ollama(str(case["case_id"]), model=model_name,
                                            base_url=base_url or "http://localhost:11434",
                                            num_ctx=num_ctx, answer_reserve_tokens=answer_reserve,
                                            think=reasoning_effort, timeout=call_timeout)
    else:
        runtime = V3CaseRuntime.from_openrouter(str(case["case_id"]), model=model_name,
                                                base_url=base_url or "https://openrouter.ai/api/v1")
    runtime.bridge.max_job_failures = max_job_failures
    trace: list[dict[str, Any]] = []
    sent: set[str] = set()
    responded: set[str] = set()
    completed_jobs: list[Any] = []
    remaining_jobs = max_jobs
    failure = None
    try:
        runtime.initialize_case(
            case_packet=dict(case["case_packet"]),
            specialist_profiles=tuple(case["specialist_profiles"]),
            initial_items=tuple(_incoming(_read_item(row, case_path.parent))
                                for row in case.get("initial_items", [])),
            submission_id=str(case.get("initial_submission_id", "initial-submission")),
        )
        if custodian_mode == "fixed":
            holdings = json.loads(holdings_path.read_text(encoding="utf-8"))
            rows_by_id = {str(row["item_id"]): _read_item(row, case_path.parent)
                          for submission in case.get("later_submissions", [])
                          for row in submission.get("items", [])}
            missing = {d["item_id"] for d in holdings["documents"]} - set(rows_by_id)
            if missing:
                raise RuntimeError(f"custodian holds items the case does not define: {sorted(missing)}")
            custodian = Custodian.from_file(holdings_path)
            chunk = chunk_jobs or int(holdings.get("policy", {}).get("chunk_jobs", 3))
            completed_jobs.extend(_drive_fixed(runtime, custodian, rows_by_id, sent, responded, trace,
                                               max_jobs=remaining_jobs, chunk=chunk))
            remaining_jobs = max_jobs - len(completed_jobs)
        else:
            initial = runtime.run_ready(max_jobs=remaining_jobs)
            completed_jobs.extend(initial)
            remaining_jobs -= len(initial)
            _dispatch_ready(runtime, sent, trace)

            for wave_index, submission in enumerate(case.get("later_submissions", [])):
                wave_id = str(submission["submission_id"])
                rows = [_read_item(row, case_path.parent) for row in submission.get("items", [])]
                _answer_requests(runtime, runtime.model_client, rows, responded, trace,
                                 final_wave=False, wave_id=wave_id)
                # Any item not used as a request-specific response remains a normal
                # unsolicited arrival. This preserves material coverage and lets the
                # Lead route it independently.
                used = {source_id for event in trace if event.get("event") == "synthetic_custodian_replied"
                        and event.get("request_id") in responded
                        for source_id in event.get("source_item_ids", [])}
                leftovers = [row for row in rows if row["item_id"] not in used]
                if leftovers:
                    runtime.submit_material(
                        submission_id=wave_id,
                        items=tuple(_incoming(row) for row in leftovers),
                        sender_id=str(submission.get("sender_id", "synthetic-case-material-upload")),
                    )
                    trace.append({"event": "fixture_material_arrival", "submission_id": wave_id,
                                  "item_ids": [row["item_id"] for row in leftovers],
                                  "arrival_index": wave_index + 1})
                if remaining_jobs > 0:
                    wave_jobs = runtime.run_ready(max_jobs=remaining_jobs)
                    completed_jobs.extend(wave_jobs)
                    remaining_jobs -= len(wave_jobs)
                _dispatch_ready(runtime, sent, trace)
                _answer_requests(runtime, runtime.model_client, rows, responded, trace,
                                 final_wave=False, wave_id=wave_id)
                if remaining_jobs > 0:
                    reply_jobs = runtime.run_ready(max_jobs=remaining_jobs)
                    completed_jobs.extend(reply_jobs)
                    remaining_jobs -= len(reply_jobs)
                _dispatch_ready(runtime, sent, trace)
                if len(trace) > max_rounds * 10:
                    raise RuntimeError("closed-loop trace cap reached; run stopped to avoid unbounded simulation")

            # Give unanswered requests a final search, then keep cycling if that
            # review creates another approved request. The hard round cap prevents
            # a model-induced request loop from running indefinitely.
            all_rows = [_read_item(row, case_path.parent) for submission in case.get("later_submissions", [])
                        for row in submission.get("items", [])]
            for round_index in range(max_rounds):
                before = len(responded)
                _dispatch_ready(runtime, sent, trace)
                _answer_requests(runtime, runtime.model_client, all_rows, responded, trace,
                                 final_wave=True, wave_id=f"final-fixture-search-{round_index + 1}")
                if len(responded) == before:
                    break
                if remaining_jobs > 0:
                    final_jobs = runtime.run_ready(max_jobs=remaining_jobs)
                    completed_jobs.extend(final_jobs)
                    remaining_jobs -= len(final_jobs)
            else:
                trace.append({"event": "round_budget_reached", "max_rounds": max_rounds})
            _dispatch_ready(runtime, sent, trace)
    except Exception as exc:  # preserve a snapshot for diagnosis
        failure = {"type": type(exc).__name__, "message": str(exc)}

    report = runtime.snapshot()
    report["closed_loop_simulation"] = {
        "mode": "fixed_custodian" if custodian_mode == "fixed" else "synthetic_fixture_custodian",
        "notice": case.get("fixture_notice", "Synthetic scenario only."),
        "outward_trace": trace,
        "dispatched_request_ids": sorted(sent),
        "responded_request_ids": sorted(responded),
        "response_policy": ("fixed deterministic custodian, independent of the model under test; "
                            "no-match is not proof of absence" if custodian_mode == "fixed" else
                            "model selects fixture IDs only; no-match is not proof of absence"),
        "actual_human_contact": False,
    }
    report["run_metadata"] = {
        "provider": provider, "model": model_name,
        # The bridge's own list stays correct when the run aborted mid-queue.
        "completed_role_jobs": [list(row) for row in runtime.bridge.completed],
        "role_job_budget": max_jobs, "role_jobs_remaining": max_jobs - len(runtime.bridge.completed),
        "round_budget": max_rounds, "custodian": custodian_mode,
        "num_ctx": num_ctx, "answer_reserve_tokens": answer_reserve, "reasoning_effort": reasoning_effort,
        "call_timeout_seconds": call_timeout,
        "max_job_failures": max_job_failures,
        "job_failures": list(runtime.bridge.job_failures),
        "specialist_prompt_omissions": list(runtime.bridge.prompt_omissions),
        "run_status": _run_status(failure, runtime.bridge.job_failures),
        "failure": failure,
        "synthetic_fixture_notice": case.get("fixture_notice", ""),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=V3_ROOT / "examples" / "r3_synthetic_case.json")
    parser.add_argument("--output", type=Path, default=Path("outputs/r3_closed_loop.json"))
    parser.add_argument("--provider", choices=("openrouter", "ollama_native"), default="openrouter")
    parser.add_argument("--model", default="nvidia/nemotron-3-ultra-550b-a55b:free")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--max-jobs", type=int, default=64)
    parser.add_argument("--max-rounds", type=int, default=12)
    parser.add_argument("--max-job-failures", type=int, default=25,
                        help="role results rejected by their own engine are recorded as failed jobs and "
                             "the run continues, up to this many; 0 aborts on the first")
    parser.add_argument("--num-ctx", type=int, default=None,
                        help="Ollama context window in tokens (ollama_native only); default is the server's")
    parser.add_argument("--answer-reserve", type=int, default=0,
                        help="tokens of the context window kept free for the Specialist's reasoning and "
                             "answer; its prompt is trimmed to fit the rest (ollama_native with --num-ctx)")
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high"), default=None,
                        help="gpt-oss reasoning effort for every role (ollama_native); default: the model's own")
    parser.add_argument("--call-timeout", type=float, default=300, help="seconds allowed for one model call")
    parser.add_argument("--custodian", choices=("fixed", "model"), default="fixed",
                        help="fixed: deterministic custodian independent of the model under test (default); "
                             "model: the legacy custodian that asks the model under test to pick documents")
    parser.add_argument("--holdings", type=Path, default=DEFAULT_HOLDINGS)
    parser.add_argument("--custodian-chunk", type=int, default=None,
                        help="role jobs to run between custodian steps (fixed custodian only)")
    args = parser.parse_args()
    if args.provider == "ollama_native" and args.model.startswith("nvidia/"):
        parser.error("--model must be an installed local Ollama tag with --provider ollama_native")
    report = run(args.case, args.output, provider=args.provider, model_name=args.model,
                 base_url=args.base_url, max_jobs=args.max_jobs, max_rounds=args.max_rounds,
                 num_ctx=args.num_ctx, answer_reserve=args.answer_reserve,
                 reasoning_effort=args.reasoning_effort, call_timeout=args.call_timeout,
                 max_job_failures=args.max_job_failures,
                 custodian_mode=args.custodian, holdings_path=args.holdings, chunk_jobs=args.custodian_chunk)
    print(json.dumps({"output": str(args.output), "case_id": report["case_id"],
                      "status": report["run_metadata"]["run_status"],
                      "board_version": report["manifest"]["board_version"],
                      "outward_events": len(report["closed_loop_simulation"]["outward_trace"]),
                      "responded_requests": report["closed_loop_simulation"]["responded_request_ids"],
                      "job_failures": len(report["run_metadata"]["job_failures"]),
                      "failure": report["run_metadata"]["failure"]}, indent=2))
    raise SystemExit(RUN_EXIT_CODES[report["run_metadata"]["run_status"]])


if __name__ == "__main__":
    main()
