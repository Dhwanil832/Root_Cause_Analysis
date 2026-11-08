#!/usr/bin/env python3
"""Launch isolated live V1, V2, and V3 runs on the bundled R3 fixture."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1_V2_RUNNER = ROOT / "scripts" / "run_r3_v1_v2_live.py"
V3_RUNNER = ROOT / "V3_Neurosymbolic_Inspired" / "scripts" / "run_v3_case.py"
DEFAULT_CASE = ROOT / "V3_Neurosymbolic_Inspired" / "examples" / "r3_synthetic_case.json"


def _launch(command: list[str], log_path: Path) -> int:
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, check=False)
    log_path.write_text(completed.stdout, encoding="utf-8")
    return completed.returncode


def _preflight(case_path: Path, *, provider: str, model: str,
              base_url: str | None) -> list[str]:
    problems: list[str] = []
    if provider == "openrouter" and not (os.getenv("OPENROUTER_API_KEY") or os.getenv("RCA_LLM_API_KEY")):
        problems.append("Set OPENROUTER_API_KEY in your shell before a live run.")
    if provider == "ollama_native":
        if model.startswith("nvidia/"):
            problems.append("Pass --model with an exact model tag installed in local Ollama.")
        try:
            sys.path.insert(0, str(ROOT / "V1_V2_Prompt_and_Rules" / "source" /
                                   "RCA_Version_Labeled_Codebase"))
            from shared.llm.ollama_client import OllamaChatModel
            OllamaChatModel(model, base_url=base_url or "http://localhost:11434",
                            timeout=5, retries=0).check_model()
        except Exception as exc:
            problems.append(f"Local Ollama preflight failed: {type(exc).__name__}: {exc}")
    if not case_path.is_file():
        problems.append(f"Case JSON does not exist: {case_path}")
        return problems
    try:
        case = json.loads(case_path.read_text(encoding="utf-8"))
        for row in case.get("initial_items", []):
            if "path" in row and not (case_path.parent / row["path"]).is_file():
                problems.append(f"Missing initial material {row.get('item_id')}: {row['path']}")
        for submission in case.get("later_submissions", []):
            for row in submission.get("items", []):
                if "path" in row and not (case_path.parent / row["path"]).is_file():
                    problems.append(f"Missing later material {row.get('item_id')}: {row['path']}")
    except (OSError, json.JSONDecodeError, AttributeError, TypeError) as exc:
        problems.append(f"Could not read case JSON: {type(exc).__name__}: {exc}")
    try:
        import clingo  # noqa: F401
    except ImportError:
        problems.append("Clingo is missing; install V3_Neurosymbolic_Inspired/requirements-sahs.txt.")
    for required in (V1_V2_RUNNER, V3_RUNNER):
        if not required.is_file():
            problems.append(f"Runner script is missing: {required}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--output", type=Path, default=Path("outputs/r3_all_versions"))
    parser.add_argument("--model", default="nvidia/nemotron-3-ultra-550b-a55b:free")
    parser.add_argument("--provider", choices=("openrouter", "ollama_native"), default="openrouter",
                        help="Use OpenRouter or the native local Ollama /api/chat endpoint")
    parser.add_argument("--base-url", default=None,
                        help="Ollama host origin (default http://localhost:11434) or OpenRouter API base URL")
    parser.add_argument("--max-actions", type=int, default=12)
    parser.add_argument("--max-v3-jobs", type=int, default=16)
    parser.add_argument("--check-only", action="store_true",
                        help="validate credentials, fixture paths, Clingo, and scripts; make no model calls")
    args = parser.parse_args()
    case_path = args.case.resolve()
    problems = _preflight(case_path, provider=args.provider, model=args.model,
                          base_url=args.base_url)
    if problems:
        print("Preflight failed; no model calls were made:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        raise SystemExit(2)
    if args.check_only:
        print("Preflight passed; no model calls were made.")
        raise SystemExit(0)
    if args.max_actions < 1 or args.max_v3_jobs < 1:
        parser.error("job limits must be positive integers")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    v1_v2_output = output / "v1_v2"
    v3_output = output / "v3_run.json"

    common = ["--case", str(case_path), "--model", args.model,
              "--provider", args.provider]
    if args.base_url:
        common.extend(["--base-url", args.base_url])
    v1_v2_code = _launch([
        sys.executable, str(V1_V2_RUNNER), *common,
        "--output", str(v1_v2_output), "--max-actions", str(args.max_actions),
    ], output / "v1_v2_console.log")
    v3_code = _launch([
        sys.executable, str(V3_RUNNER), *common,
        "--output", str(v3_output), "--include-later-materials",
        "--max-jobs", str(args.max_v3_jobs),
    ], output / "v3_console.log")

    v1_v2_report_path = v1_v2_output / "V1_V2_R3_REPORT.json"
    v1_v2_report = json.loads(v1_v2_report_path.read_text(encoding="utf-8")) if v1_v2_report_path.exists() else None
    v3_report = json.loads(v3_output.read_text(encoding="utf-8")) if v3_output.exists() else None
    v1_v2_profiles = (v1_v2_report or {}).get("profiles", [])
    v1_v2_all_completed = bool(v1_v2_profiles) and all(
        row.get("run_status") == "completed" for row in v1_v2_profiles)
    v3_run_status = (v3_report or {}).get("run_metadata", {}).get("run_status")
    overall_status = "completed" if (
        v1_v2_code == 0 and v3_code == 0 and v1_v2_all_completed
        and v3_run_status == "completed"
    ) else "failed_or_partial"
    summary = {
        "case_id": json.loads(case_path.read_text(encoding="utf-8"))["case_id"],
        "provider": args.provider,
        "model": args.model,
        "execution_order": ["V1", "V2", "V3"],
        "run_status": overall_status,
        "v1_v2_exit_code": v1_v2_code,
        "v1_v2_profiles": v1_v2_profiles,
        "v3_exit_code": v3_code,
        "v3_run_status": v3_run_status,
        "v1_v2_report": str(v1_v2_report_path) if v1_v2_report else None,
        "v3_report": str(v3_output) if v3_report else None,
        "interpretation_limit": (
            "Exploratory live pipeline trial over the same synthetic fixture corpus. "
            "V1/V2 release documents through their custodian/request loop; V3 applies "
            "the staged PIRIS material arrivals. This is not a controlled causal-quality comparison."
        ),
    }
    (output / "ALL_VERSIONS_REPORT.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if overall_status != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
