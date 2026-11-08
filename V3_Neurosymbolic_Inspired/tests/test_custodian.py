"""The fixed custodian: determinism, timing, reply types, and the runner's chunked driver."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from orchestration.custodian import Custodian, Holding, RequestView, Statement, words

V3 = Path(__file__).resolve().parents[1]
HOLDINGS_FILE = V3.parent / "ground_truth" / "custodian_holdings.json"
_SPEC = importlib.util.spec_from_file_location("run_v3_closed_loop", V3 / "scripts" / "run_v3_closed_loop.py")
runner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runner)


def make(**kw):
    holdings = (
        Holding("E08", 20, 50, words("valve workshop seepage examination leak bench hydraulic")),
        Holding("E10", 30, 30, words("outage switching shutdown utility supply hydraulic desk")),
        Holding("E14", 60, 70, words("action register redesign status corrective")),
    )
    statements = (Statement("S1", words("who holds owner ownership records"),
                            "Maintenance records holds work instructions."),)
    return Custodian(holdings=holdings, statements=statements, reply_delay=kw.pop("reply_delay", 6),
                     off_topic_every=kw.pop("off_topic_every", 3), **kw)


def req(rid, text, slots=()):
    return RequestView(rid, text, tuple(slots))


class Replies(unittest.TestCase):
    def test_nothing_before_the_reply_delay(self):
        c = make()
        self.assertEqual(c.step(0, [req("R1", "valve workshop seepage examination")]), [])
        self.assertEqual(c.step(5, [req("R1", "valve workshop seepage examination")]), [])

    def test_matching_available_document_is_delivered_after_the_delay(self):
        c = make()
        c.step(20, [req("R1", "valve workshop seepage examination")])          # first seen at 20
        actions = c.step(26, [req("R1", "valve workshop seepage examination")])
        docs = [a for a in actions if a["kind"] == "documents"]
        self.assertEqual(docs[0]["item_ids"], ["E08"])
        self.assertEqual(docs[0]["request_id"], "R1")

    def test_waits_for_a_held_document_that_is_not_yet_available(self):
        c = make()
        r = [req("R1", "valve workshop seepage examination")]
        c.step(0, r)
        self.assertEqual(c.step(10, r), [])                      # E08 is available at 20
        self.assertEqual(c.next_due(10, r), 20)
        self.assertEqual(c.step(20, r)[0]["item_ids"], ["E08"])

    def test_one_shared_word_is_not_a_match(self):
        c = make()
        c.step(0, [req("R1", "valve")])
        actions = c.step(30, [req("R1", "valve")])
        self.assertEqual([a["kind"] for a in actions if a.get("request_id")], ["no_record"])

    def test_slots_are_answered_only_when_the_document_covers_them(self):
        c = make()
        slots = [("s1", "valve seepage examination"), ("s2", "pressure trace historian")]
        r = [req("R1", "valve workshop seepage examination pressure trace", slots)]
        c.step(0, r)
        action = c.step(25, r)[0]
        self.assertEqual(action["answered_slot_ids"], ["s1"])
        self.assertEqual(action["stance"], "partial")

    def test_statement_answers_when_no_document_matches(self):
        c = make()
        c.step(0, [req("R1", "who holds the records")])
        action = c.step(6, [req("R1", "who holds the records")])[0]
        self.assertEqual(action["kind"], "statement")
        self.assertEqual(action["statement_id"], "S1")

    def test_unmatched_request_gets_an_explicit_no_record(self):
        c = make()
        c.step(0, [req("R1", "photographs of the scaffold")])
        self.assertEqual(c.step(6, [req("R1", "photographs of the scaffold")])[0]["kind"], "no_record")

    def test_every_nth_unmatched_request_gets_an_unrelated_document(self):
        c = make(off_topic_every=2)
        kinds = []
        for i in range(4):
            r = [req(f"R{i}", f"unrelated topic number {i} zebra")]
            c.step(30, r)
            a = c.step(36, r)[0]
            kinds.append((a["kind"], a["stance"]))
        self.assertEqual([k for k, _ in kinds], ["no_record", "documents", "no_record", "no_record"])
        self.assertEqual(kinds[1][1], "off_topic")

    def test_a_request_is_answered_once(self):
        c = make()
        r = [req("R1", "valve workshop seepage examination")]
        c.step(20, r)
        c.step(26, r)
        self.assertEqual([a for a in c.step(40, r) if a.get("request_id")], [])


class Arrivals(unittest.TestCase):
    def test_unprompted_document_arrives_at_its_time_once(self):
        c = make()
        self.assertEqual(c.step(29, []), [])
        first = c.step(30, [])
        self.assertEqual(first, [{"kind": "unprompted", "item_ids": ["E10"]}])
        self.assertEqual(c.step(31, []), [])

    def test_a_document_sent_as_a_reply_does_not_arrive_again(self):
        c = make()
        r = [req("R1", "valve workshop seepage examination")]
        c.step(20, r)
        c.step(26, r)
        self.assertNotIn("E08", [i for a in c.step(60, []) for i in a.get("item_ids", [])])

    def test_next_due_is_none_when_nothing_remains(self):
        c = make()
        c.step(100, [])
        self.assertIsNone(c.next_due(100, []))


class Independence(unittest.TestCase):
    def test_same_inputs_give_the_same_actions(self):
        runs = []
        for _ in range(2):
            c, out = make(), []
            for clock in range(0, 80, 4):
                out.append(c.step(clock, [req("R1", "valve workshop seepage examination"),
                                          req("R2", "photographs of the scaffold")]))
            runs.append(out)
        self.assertEqual(runs[0], runs[1])

    def test_module_does_not_use_a_model(self):
        source = (V3 / "orchestration" / "custodian.py").read_text(encoding="utf-8")
        self.assertNotIn(".ask(", source)
        self.assertNotIn("model_client", source)


class HoldingsFile(unittest.TestCase):
    def test_real_holdings_load_and_match_the_case_documents(self):
        c = Custodian.from_file(HOLDINGS_FILE)
        case = json.loads((V3 / "examples" / "r3_synthetic_case.json").read_text(encoding="utf-8"))
        later = {row["item_id"] for s in case["later_submissions"] for row in s["items"]}
        self.assertEqual({h.item_id for h in c.holdings}, later)
        self.assertTrue(all(len(h.topics) >= 4 for h in c.holdings))

    def test_the_misfiled_switching_sheet_arrives_unprompted(self):
        c = Custodian.from_file(HOLDINGS_FILE)
        e10 = next(h for h in c.holdings if h.item_id == "E10")
        self.assertEqual(e10.unprompted_at, e10.available_at)

    def test_a_real_valve_request_reaches_the_workshop_record(self):
        c = Custodian.from_file(HOLDINGS_FILE)
        r = [req("R1", "Please provide the valve workshop examination record for IV-RB3-17")]
        c.step(30, r)
        actions = c.step(36, r)
        self.assertEqual([a for a in actions if a["kind"] == "documents"][0]["item_ids"][0], "E08")


class FakeRuntime:
    """Stands in for V3CaseRuntime: a queue of jobs and a record of what was submitted when."""

    def __init__(self, jobs):
        self.pending, self.done, self.submissions = jobs, [], []

    def run_ready(self, *, max_jobs):
        batch, self.pending = self.pending[:max_jobs], self.pending[max_jobs:]
        self.done += batch
        return batch

    def submit_material(self, **kw):
        self.submissions.append({"after_jobs": len(self.done), "queued": len(self.pending), **kw})


ROWS = {i: {"item_id": i, "text": f"text {i}", "filename": f"{i}.md", "declared_kind": "case_material"}
        for i in ("E08", "E10", "E14")}


def drive(runtime, custodian, views=(), **kw):
    sent, responded, trace = set(), set(), []
    open_requests = lambda rt, s, r: [v for v in views if v.request_id not in r]
    with patch.object(runner, "_dispatch_ready"), patch.object(runner, "_open_requests", open_requests):
        done = runner._drive_fixed(runtime, custodian, ROWS, sent, responded, trace,
                                   max_jobs=kw.get("max_jobs", 100), chunk=kw.get("chunk", 3))
    return done, trace


class Driver(unittest.TestCase):
    def test_document_arrives_while_work_is_still_queued(self):
        rt = FakeRuntime(list(range(40)))
        drive(rt, make())
        e10 = next(s for s in rt.submissions if s["submission_id"].startswith("custodian-arrival"))
        self.assertGreaterEqual(e10["after_jobs"], 30)
        self.assertGreater(e10["queued"], 0)
        self.assertEqual([i.item_id for i in e10["items"]][0:1], ["E10"][0:1])

    def test_idle_system_waits_for_a_held_document_then_gets_the_reply(self):
        rt = FakeRuntime([])
        views = [req("R1", "valve workshop seepage examination")]
        done, trace = drive(rt, make(), views)
        replies = [e for e in trace if e["event"] == "synthetic_custodian_replied"]
        self.assertEqual(replies[0]["source_item_ids"], ["E08"])
        self.assertGreaterEqual(replies[0]["clock"], 20)
        self.assertEqual(done, [])

    def test_unanswerable_request_ends_with_a_no_record_note(self):
        rt = FakeRuntime([])
        _done, trace = drive(rt, make(), [req("R1", "photographs of the scaffold")])
        self.assertIn("synthetic_custodian_no_match", [e["event"] for e in trace])

    def test_budget_exhaustion_stops_the_driver_and_says_so(self):
        rt = FakeRuntime(list(range(50)))
        done, trace = drive(rt, make(), max_jobs=7)
        self.assertEqual(len(done), 7)
        self.assertIn("job_budget_exhausted", [e["event"] for e in trace])

    def test_driver_ends_when_nothing_is_left_to_do(self):
        rt = FakeRuntime([])
        _done, trace = drive(rt, make())
        arrivals = [e for e in trace if e["event"] == "fixture_material_arrival"]
        self.assertEqual({i for e in arrivals for i in e["item_ids"]}, {"E08", "E10", "E14"})
        self.assertNotIn("driver_step_cap_reached", [e["event"] for e in trace])

    def test_two_runs_with_the_same_job_count_see_the_same_arrivals(self):
        traces = []
        for _ in range(2):
            _d, t = drive(FakeRuntime(list(range(25))), make(), [req("R1", "valve workshop seepage")])
            traces.append([(e["event"], e.get("clock"), tuple(e.get("item_ids", e.get("source_item_ids", [])))) for e in t])
        self.assertEqual(traces[0], traces[1])


if __name__ == "__main__":
    unittest.main()
