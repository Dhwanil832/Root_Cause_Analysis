"""The repeat-run tool: spread across runs, agreement between runs, raw responses dropped."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

_SPEC = importlib.util.spec_from_file_location(
    "run_repeats", Path(__file__).resolve().parents[1] / "scripts" / "run_repeats.py")
rr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rr)


def sig(nodes=(), sentences=(), documents=()):
    return {"nodes": set(nodes), "sentences": set(sentences), "documents": set(documents)}


def row(status="completed", cov=0.5, recall=0.5, off=0.5, signature=None, jobs=10):
    return {"status": status, "node_coverage": cov, "key_sentence_recall": recall,
            "claims_off_chart_share": off, "jobs_executed": jobs, "assessments": 20,
            "nothing_extracted_share": 0.5, "model_calls_accepted": 30,
            "signature": signature or sig()}


class Summary(unittest.TestCase):
    def test_spread_of_a_metric(self):
        out = rr.summarise([row(cov=0.2), row(cov=0.4), row(cov=0.6)])
        self.assertEqual(out["node_coverage"], {"mean": 0.4, "min": 0.2, "max": 0.6})
        self.assertEqual(out["runs"], 3)

    def test_identical_runs_agree_fully(self):
        s = sig(nodes={"G13"}, sentences={("E08", "n", "supports")}, documents={"E08"})
        out = rr.summarise([row(signature=s), row(signature=s)])
        self.assertEqual(out["agreement_nodes"], 1.0)
        self.assertEqual(out["agreement_sentences"], 1.0)

    def test_disjoint_runs_do_not_agree(self):
        out = rr.summarise([row(signature=sig(nodes={"G13"})), row(signature=sig(nodes={"G07"}))])
        self.assertEqual(out["agreement_nodes"], 0.0)

    def test_partial_overlap_is_a_ratio(self):
        out = rr.summarise([row(signature=sig(nodes={"G1", "G2"})), row(signature=sig(nodes={"G2", "G3"}))])
        self.assertAlmostEqual(out["agreement_nodes"], 0.33, places=2)

    def test_single_run_has_no_agreement_figure(self):
        self.assertIsNone(rr.summarise([row()])["agreement_nodes"])

    def test_statuses_are_listed_so_a_failed_run_is_not_hidden(self):
        out = rr.summarise([row(status="completed"), row(status="failed_or_partial")])
        self.assertEqual(out["status"], ["completed", "failed_or_partial"])


class OneRun(unittest.TestCase):
    def args(self, tmp, keep_raw=False):
        return SimpleNamespace(
            output_prefix=Path(tmp) / "exp", case=Path("c.json"), provider="ollama_native", model="m",
            base_url=None, max_jobs=5, max_rounds=2, num_ctx=1024, answer_reserve=0, reasoning_effort=None, call_timeout=300, max_job_failures=3,
            holdings=Path("h.json"), custodian_chunk=None, keep_raw=keep_raw)

    def fake_report(self):
        return {"board": {"claims": [], "assessments": [], "materials": []}, "work": [],
                "model_raw_responses": [{"task": "x", "outcome": "accepted"}] * 4,
                "closed_loop_simulation": {}, "run_metadata": {"run_status": "completed"}}

    def run_one(self, keep_raw):
        with tempfile.TemporaryDirectory() as tmp:
            truth = rr.truth_score.load_truth()
            captured = {}

            def fake_run(case, output, **kw):
                captured.update(kw, output=output)
                output.write_text("{}", encoding="utf-8")
                return self.fake_report()
            with patch.object(rr.loop, "run", fake_run):
                result = rr.one_run(2, self.args(tmp, keep_raw), truth)
            saved = json.loads(Path(result["file"]).read_text(encoding="utf-8"))
            return result, saved, captured

    def test_runs_use_the_fixed_custodian_and_numbered_files(self):
        result, _saved, captured = self.run_one(keep_raw=False)
        self.assertEqual(captured["custodian_mode"], "fixed")
        self.assertTrue(result["file"].endswith("exp_run2.json"))

    def test_raw_responses_are_dropped_by_default_and_counted(self):
        _r, saved, _c = self.run_one(keep_raw=False)
        self.assertNotIn("model_raw_responses", saved)
        self.assertEqual(saved["model_raw_responses_dropped"], 4)

    def test_keep_raw_leaves_the_file_as_the_runner_wrote_it(self):
        _r, saved, _c = self.run_one(keep_raw=True)
        self.assertEqual(saved, {})


if __name__ == "__main__":
    unittest.main()
