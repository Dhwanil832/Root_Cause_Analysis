#!/usr/bin/env python3
"""Run the original V1 and V2 pipelines against the bundled synthetic R3 case."""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "V1_V2_Prompt_and_Rules" / "source" / "RCA_Version_Labeled_Codebase"
sys.path.insert(0, str(LEGACY))

from evaluation.run_matrix import run_matrix  # noqa: E402


def _source_paths(case_path: Path, case: dict) -> dict[str, Path]:
    rows = list(case.get("initial_items", []))
    for submission in case.get("later_submissions", []):
        rows.extend(submission.get("items", []))
    found = {}
    for row in rows:
        source = (case_path.parent / row["path"]).resolve()
        found[str(row["item_id"])] = source
    return found


def _slug(owner: str) -> str:
    parts = re.findall(r"[a-z0-9]+", owner.casefold())
    return "_".join(parts) or "unassigned_records"


def run(case_path: Path, output: Path, *, model: str, max_actions: int,
        provider: str = "openrouter", base_url: str | None = None) -> dict:
    case_path = case_path.resolve()
    case = json.loads(case_path.read_text(encoding="utf-8"))
    sources = _source_paths(case_path, case)
    incident_ids = {str(row["item_id"]) for row in case.get("initial_items", [])}
    incident_id = "E01" if "E01" in incident_ids else next(iter(incident_ids), None)
    if not incident_id or incident_id not in sources:
        raise ValueError("case file must include an initial incident item")
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="r3-v1-v2-evidence-", dir=output) as temp:
        evidence_root = Path(temp) / "evidence"
        evidence_root.mkdir()
        owners: dict[str, list[tuple[str, Path]]] = {}
        for source_id, source_path in sorted(sources.items()):
            if source_id == incident_id:
                continue
            text = source_path.read_text(encoding="utf-8")
            owner_match = re.search(r"^Record owner:\s*(.+?)\s*$", text,
                                    flags=re.IGNORECASE | re.MULTILINE)
            owner = owner_match.group(1).strip() if owner_match else "Unassigned records"
            owners.setdefault(owner, []).append((source_id, source_path))

        for owner, documents in owners.items():
            route_dir = evidence_root / _slug(owner)
            route_dir.mkdir()
            (route_dir / "route_description.md").write_text(
                f"This custodian handles requests concerning {owner} records for this case. "
                "Specify the needed record type, entity, time range, and fields. "
                "The route may not hold every requested record.\n",
                encoding="utf-8",
            )
            for _source_id, source_path in documents:
                (route_dir / source_path.name).write_text(
                    source_path.read_text(encoding="utf-8"), encoding="utf-8")

        result = run_matrix(
            output=output / "v1_v2",
            mode="live",
            profiles=("v1_prompt_only", "v2_full"),
            max_actions=max_actions,
            model=model,
            provider=provider,
            incident=sources[incident_id],
            evidence_dir=evidence_root,
            case_id=str(case["case_id"]),
            base_url=base_url,
        )
    (output / "V1_V2_R3_REPORT.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=ROOT / "V3_Neurosymbolic_Inspired" /
                        "examples" / "r3_synthetic_case.json")
    parser.add_argument("--output", type=Path, default=Path("outputs/r3_v1_v2"))
    parser.add_argument("--model", default="nvidia/nemotron-3-ultra-550b-a55b:free")
    parser.add_argument("--provider", choices=("openrouter", "ollama_native"), default="openrouter")
    parser.add_argument("--base-url", default=None,
                        help="For ollama_native, the local Ollama origin (default http://localhost:11434)")
    parser.add_argument("--max-actions", type=int, default=12)
    args = parser.parse_args()
    if args.provider == "ollama_native" and args.model.startswith("nvidia/"):
        parser.error("--model must be an installed local Ollama tag when --provider ollama_native")
    report = run(args.case, args.output, model=args.model, max_actions=args.max_actions,
                 provider=args.provider, base_url=args.base_url)
    print(json.dumps({
        "report": str(args.output / "V1_V2_R3_REPORT.json"),
        "profiles": report["profiles"],
        "model": args.model,
    }, indent=2))
    if not report["profiles"] or any(
        row.get("run_status") != "completed" for row in report["profiles"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
