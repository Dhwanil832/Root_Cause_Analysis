#!/usr/bin/env python3
"""Run the full V3 Intake -> Lead -> Specialist -> EW -> Assessor path.

The case file contains paths to text materials. Live model credentials are read
from OPENROUTER_API_KEY; never put a key in the case JSON or command line.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

V3_ROOT = Path(__file__).resolve().parents[1]
COMBINED_ROOT = V3_ROOT.parent
LEGACY_ROOT = (COMBINED_ROOT / "V1_V2_Prompt_and_Rules" / "source" /
               "RCA_Version_Labeled_Codebase")
for path in (LEGACY_ROOT, V3_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from orchestration.v3_runtime import V3CaseRuntime  # noqa: E402
from piris import IncomingItem  # noqa: E402


def _load_items(rows: list[dict], case_dir: Path) -> tuple[IncomingItem, ...]:
    items = []
    for row in rows:
        if "path" in row:
            source = (case_dir / row["path"]).resolve()
            text = source.read_text(encoding="utf-8")
            filename = row.get("filename", source.name)
        else:
            text = str(row.get("text", ""))
            filename = str(row.get("filename", f"{row['item_id']}.txt"))
        items.append(IncomingItem.text(
            str(row["item_id"]), text,
            media_type=str(row.get("media_type", "text/markdown")),
            filename=filename,
            declared_kind=str(row.get("declared_kind", "case_material")),
            declared_request_id=row.get("declared_request_id"),
            declared_revision_of=row.get("declared_revision_of"),
            metadata=dict(row.get("metadata", {})),
        ))
    return tuple(items)


def run(case_path: Path, output_path: Path, *, model: str,
        include_later_materials: bool, max_jobs: int,
        provider: str = "openrouter", base_url: str | None = None) -> dict:
    case_path = case_path.resolve()
    case = json.loads(case_path.read_text(encoding="utf-8"))
    if provider == "ollama_native":
        runtime = V3CaseRuntime.from_ollama(
            str(case["case_id"]), model=model,
            base_url=base_url or "http://localhost:11434",
            enable_intake_interpreter=True, enable_lead_semantics=True,
        )
    else:
        runtime = V3CaseRuntime.from_openrouter(
            str(case["case_id"]), model=model,
            base_url=base_url or "https://openrouter.ai/api/v1",
            enable_intake_interpreter=True,
            enable_lead_semantics=True,
        )
    completed = []
    failure = None
    remaining_jobs = max_jobs
    try:
        runtime.initialize_case(
            case_packet=dict(case["case_packet"]),
            specialist_profiles=tuple(case["specialist_profiles"]),
            initial_items=_load_items(case.get("initial_items", []), case_path.parent),
            submission_id=str(case.get("initial_submission_id", "initial-submission")),
        )
        if remaining_jobs > 0:
            first_wave = runtime.run_ready(max_jobs=remaining_jobs)
            completed.extend(first_wave)
            remaining_jobs -= len(first_wave)
        if include_later_materials:
            for submission in case.get("later_submissions", []):
                runtime.submit_material(
                    submission_id=str(submission["submission_id"]),
                    items=_load_items(submission.get("items", []), case_path.parent),
                    sender_id=str(submission.get("sender_id", "case-material-upload")),
                )
                if remaining_jobs > 0:
                    next_wave = runtime.run_ready(max_jobs=remaining_jobs)
                    completed.extend(next_wave)
                    remaining_jobs -= len(next_wave)
    except Exception as exc:
        failure = {"type": type(exc).__name__, "message": str(exc)}

    report = runtime.snapshot()
    report["run_metadata"] = {
        "provider": provider,
        "model": model,
        "include_later_materials": include_later_materials,
        "completed_role_jobs": [list(row) for row in completed],
        "role_job_budget": max_jobs,
        "role_jobs_remaining": remaining_jobs,
        "run_status": "failed_or_partial" if failure else "completed",
        "failure": failure,
        "synthetic_fixture_notice": case.get("fixture_notice", ""),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True, help="V3 case JSON")
    parser.add_argument("--output", type=Path, default=Path("outputs/v3_run.json"))
    parser.add_argument("--model", default="nvidia/nemotron-3-ultra-550b-a55b:free",
                        help="OpenRouter model ID, or an exact installed Ollama tag with --provider ollama_native")
    parser.add_argument("--provider", choices=("openrouter", "ollama_native"), default="openrouter")
    parser.add_argument("--base-url", default=None,
                        help="Provider API base URL; native Ollama defaults to http://localhost:11434")
    parser.add_argument("--include-later-materials", action="store_true",
                        help="ingest later case materials as a second PIRIS submission")
    parser.add_argument("--max-jobs", type=int, default=16,
                        help="total role-job cap across the run (model calls can be higher)")
    args = parser.parse_args()
    if args.provider == "ollama_native" and args.model.startswith("nvidia/"):
        parser.error("--model must be an installed local Ollama tag when --provider ollama_native")
    report = run(args.case, args.output, model=args.model,
                 include_later_materials=args.include_later_materials,
                 max_jobs=args.max_jobs, provider=args.provider, base_url=args.base_url)
    print(json.dumps({
        "output": str(args.output),
        "case_id": report["case_id"],
        "board_version": report["manifest"]["board_version"],
        "claims": len(report["board"]["claims"]),
        "assessments": len(report["board"]["assessments"]),
        "requests": len(report["board"]["requests"]),
        "model_calls": len(report["model_calls"]),
        "open_work": sum(1 for item in report["work"]
                         if item["state"] in {"queued", "running", "awaiting_assessor",
                                               "needs_revision", "waiting_external"}),
    }, indent=2))
    if report["run_metadata"]["run_status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
