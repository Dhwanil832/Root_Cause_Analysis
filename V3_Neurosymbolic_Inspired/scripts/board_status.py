#!/usr/bin/env python3
"""Show the status of every claim and link on a saved run's board, and its causal chains.

Uses the same rules as the Lead (``cferp/status.py``) and needs no model. Boards from
before v0.5 have no claim parts or denials and only ``neutral`` for passages that settle
nothing, so each claim reads as one part and ``neutral`` as ``open``. Origins (a recap
counted as the record it was prepared from) are worked out from the documents' text.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cferp.status import board_status  # noqa: E402


def render(report: dict, view: dict, max_paths: int) -> str:
    texts = {c["claim_id"]: c.get("text", "") for c in report["board"]["claims"]}
    docs = {m["material_id"]: m.get("title", m["material_id"]).removesuffix(".md")
            for m in report["board"].get("materials", ())}
    out = [f"claims by status: {view['claims_by_status']}", f"links by status:  {view['links_by_status']}", ""]
    order = ["reported", "shown", "partly shown", "contested", "contradicted", "open", "unchecked"]
    for status in order:
        rows = [r for r in view["claims"].values() if r["status"] == status]
        if not rows:
            continue
        out.append(f"{status.upper()} ({len(rows)})")
        for r in sorted(rows, key=lambda r: r["claim_id"]):
            src = sorted({docs.get(s, s) for p in r["parts"] for s in p["support_sources"]})
            con = sorted({docs.get(s, s) for p in r["parts"] for s in p["contradict_sources"]})
            extra = (f" supports {','.join(src)}" if src else "") + (f" contradicts {','.join(con)}" if con else "")
            out.append(f"  {r['claim_id']}: {texts.get(r['claim_id'], '')[:90]}{extra}  {r['assessments_by_effect']}")
        out.append("")
    chains = view["chains"]
    paths = chains["paths"]
    out.append(f"CHAINS: {len(paths)} paths from the incident{' (truncated)' if chains['truncated'] else ''}; "
               f"{len(chains['claims_on_no_path'])} claims on no path")
    out.append(f"  weakest claim on each path: {dict(Counter(p['weakest_claim']['status'] for p in paths))}")
    # Two links between the same claims give two paths; print each chain of claims once.
    chains_seen = Counter()
    for p in paths:
        chains_seen[" <- ".join(f"{i}[{s}]" for (k, i), s in zip(p["steps"], p["statuses"]) if k == "claim")] += 1
    for line, n in list(chains_seen.items())[:max_paths]:
        out.append(f"  {line}{f'  (x{n}, by different links)' if n > 1 else ''}")
    if chains["claims_on_no_path"]:
        out.append("  on no path: " + ", ".join(chains["claims_on_no_path"]))
    out.append("")
    out.append("ORIGINS: " + (", ".join(f"{docs.get(d, d)} prepared from {docs.get(o, o)}"
                                        for d, o in sorted(view["origins"].items())) or "none found"))
    conflicts = view["denial_conflicts"]
    out.append(f"DENIAL CONFLICTS ({len(conflicts)}): passages supporting a claim and one it denies")
    for c in conflicts:
        out.append(f"  {docs.get(c['material_id'], c['material_id'])} {c['passage_id']}: " + " vs ".join(c["claims"]))
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-paths", type=int, default=40)
    args = parser.parse_args()
    report = json.loads(args.run.read_text(encoding="utf-8"))
    view = board_status(report["board"])
    print(json.dumps(view, indent=1) if args.json else render(report, view, args.max_paths))


if __name__ == "__main__":
    main()
