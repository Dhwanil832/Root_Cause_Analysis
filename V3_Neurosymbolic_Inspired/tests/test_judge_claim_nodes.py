"""The claim-to-node judge: its prompt inputs, answer cleanup and agreement measure."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))
_SPEC = importlib.util.spec_from_file_location("judge_claim_nodes", _SCRIPTS / "judge_claim_nodes.py")
jcn = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(jcn)


def nodes(*pairs):
    return [{"id": i, "fit": f} for i, f in pairs]


class ScriptedClient:
    def __init__(self, reply):
        self.reply = reply

    def ask(self, task, system, payload):
        return self.reply


class Judge(unittest.TestCase):
    def test_chart_nodes_leave_out_the_focal_event_and_carry_evidence_map_notes(self):
        rows = jcn.chart_nodes(jcn.TRUTH_DIR)
        ids = [r["id"] for r in rows]
        self.assertNotIn("G00", ids)
        self.assertIn("note", rows[ids.index("G13")])

    def test_repeated_node_in_an_answer_is_kept_once(self):
        client = ScriptedClient({"nodes": nodes(("G13", "same"), ("G13", "part")), "reason": "r"})
        self.assertEqual(jcn.judge(client, [], "claim")["nodes"], nodes(("G13", "same")))

    def test_schema_allows_only_chart_node_ids(self):
        s = jcn.schema(["G01", "G02"])
        self.assertEqual(s["properties"]["nodes"]["items"]["properties"]["id"]["enum"], ["G01", "G02"])


class Agreement(unittest.TestCase):
    def test_same_and_part_both_count_as_a_match(self):
        out = jcn.agreement([{"human": nodes(("G13", "same")), "judge": nodes(("G13", "part"))}])
        self.assertEqual((out["claims_in_full_agreement"], out["node_match_precision"]), (1, 1.0))

    def test_extra_and_missing_nodes_lower_precision_and_recall(self):
        out = jcn.agreement([{"human": nodes(("G13", "part"), ("G07", "part")),
                              "judge": nodes(("G13", "part"), ("G02", "part"))}])
        self.assertEqual((out["node_match_precision"], out["node_match_recall"]), (0.5, 0.5))
        self.assertEqual(out["claims_in_full_agreement"], 0)

    def test_opposite_must_agree_for_full_agreement(self):
        out = jcn.agreement([{"human": nodes(("G13", "opposite")), "judge": []}])
        self.assertEqual(out["claims_in_full_agreement"], 0)

    def test_claims_with_no_node_are_counted_when_the_judge_leaves_them_empty(self):
        out = jcn.agreement([{"human": [], "judge": []}, {"human": [], "judge": nodes(("G04", "part"))}])
        self.assertEqual((out["no_node_claims"], out["no_node_claims_judge_left_empty"]), (2, 1))


if __name__ == "__main__":
    unittest.main()
