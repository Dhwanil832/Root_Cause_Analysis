"""Lead changes for v0.5 Step 1: claim parts and denials on the board, one Assessor part
per claim part, the Assessor's answers kept as they are, denial conflicts and origins."""
from __future__ import annotations

import unittest

from cferp import CFERPWorkflow, RoleResult
from cferp.contracts import Role
from cferp.integration import hera_result_to_cferp, hera_task_from_cferp
from cferp.status import board_status
from cferp.workflow import AssessmentEffect, MaterialRecord
from hera1 import Hera1Engine

from test_hera1 import FixedVersions, ScriptedModel

PASSAGE = "The B hydraulic supply was isolated at 11:10 on the switching sheet."
CLAIM = "Valve IV-RB3-17 was isolated at 11:10."
PARTS = ["Valve IV-RB3-17", "was isolated", "at 11:10"]


def workflow():
    wf = CFERPWorkflow("CASE-9")
    wf.register_material(event_id="MAT-E1", material=MaterialRecord(
        "DOC-1", "v1", "hash-1", "Switching sheet", "record", content=PASSAGE))
    specialist = wf.initialize_case(
        event_id="CASE-E1",
        case_packet={"reported_claims": [{"claim_id": "H0", "text": "Carrier beam fell", "kind": "case_claim"}]},
        specialist_profiles=({"profile_id": "other", "cues": [], "direction": "check alternatives"},))[0]
    wf.start_assignment(specialist.assignment_id)
    return wf, specialist


def propose(wf, specialist, claims):
    slot = {"slot_id": "s1", "description": "isolation record", "entity_id": "valve",
            "time_scope": "incident", "record_type": "record"}
    return wf.submit_specialist_result(RoleResult("SR-1", specialist.assignment_id, Role.SPECIALIST,
        specialist.manifest, {"claims": claims,
            "needs": [{"need_id": "N1", "target_ids": ["V"], "source_scope": ["DOC-1"], "slots": [slot]}]}))


def claim(cid, text, **extra):
    return {"claim_id": cid, "text": text, "branch_id": "B1", "kind": "component_state",
            "parent_claim_ids": ["H0"], **extra}


def review_assignment(wf, created):
    worker = next(a for a in created if a.role == Role.EVIDENCE_WORKER)
    wf.start_assignment(worker.assignment_id)
    link = {"claim_id": "V", "need_ids": ["N1"], "material_id": "DOC-1", "material_version": "v1",
            "passage_id": "p1", "exact_text": PASSAGE, "start_offset": 0, "end_offset": len(PASSAGE)}
    reviewers = wf.submit_worker_result(RoleResult("EW-1", worker.assignment_id, Role.EVIDENCE_WORKER,
        worker.manifest, {"packets": [{"packet_id": "P-N1", "target_ids": ["V"], "covered_slot_ids": ["s1"],
            "source_scope": ["DOC-1"], "entity_ids": ["valve"], "time_scope": "incident",
            "record_types": ["record"], "source_versions": wf.lead.manifest().source_versions,
            "candidate_links": [link]}]}))
    review = next(a for a in reviewers if a.context.get("task_kind") == "evidence_review")
    wf.start_assignment(review.assignment_id)
    return review


def finding(relation, statement_ids=("s1",)):
    bridge = "it bears on the part" if relation in {"supports", "consistent_with", "weakens", "contradicts"} else ""
    return {"relation": relation, "statement_ids": list(statement_ids), "rationale": relation,
            "inference_bridge": bridge, "relevance_status": "direct",
            "scope_alignment": "match", "time_alignment": "match"}


class ClaimsCarryPartsAndDenials(unittest.TestCase):
    def test_parts_and_denials_reach_the_board(self):
        wf, specialist = workflow()
        propose(wf, specialist, [claim("V", CLAIM, parts=PARTS),
                                 claim("NOT-V", "Valve IV-RB3-17 was not isolated.", denies=["V", "GHOST", "NOT-V"])])
        self.assertEqual(wf.claims["V"].parts, tuple(PARTS))
        self.assertEqual(wf.claims["NOT-V"].denies, ("V",))  # unknown and self-denial dropped


class AssessorGetsEachPart(unittest.TestCase):
    def setUp(self):
        self.wf, specialist = workflow()
        created = propose(self.wf, specialist, [claim("V", CLAIM, parts=PARTS)])
        self.review = review_assignment(self.wf, created)
        self.task = hera_task_from_cferp(self.review, self.wf)

    def test_one_assessor_part_per_claim_part_with_the_whole_claim_beside_it(self):
        parts = self.task.hypothesis["parts"]
        self.assertEqual([p["text"] for p in parts], PARTS)
        self.assertEqual({p["claim_text"] for p in parts}, {CLAIM})
        # a component state is an incident fact, so the Assessor's incident checks apply
        self.assertEqual({p["claim_type"] for p in parts}, {"incident_fact"})

    def test_each_row_names_its_part_and_keeps_the_assessors_answer(self):
        parts = self.task.hypothesis["parts"]
        statement = {"statement_id": "s1", "material_id": "p1", "source_id": "DOC-1", "source_version": "v1",
                     "representation_id": "DOC-1:v1:text", "quote": PASSAGE, "start_offset": 0,
                     "kind": "incident_observation", "modality": "asserted", "scope": "incident",
                     "timing": "incident"}
        compared = {"parts": [
            {"part_id": parts[0]["part_id"], "findings": [finding("does_not_address")]},
            {"part_id": parts[1]["part_id"], "findings": [finding("supports")]},
            {"part_id": parts[2]["part_id"], "findings": [finding("supports")]}]}
        versions = FixedVersions(self.task.case_snapshot_id, self.task.board_version, {"DOC-1": "v1"})
        result = Hera1Engine(ScriptedModel([{"statements": [statement]}, compared]), versions).run(self.task)
        self.wf.submit_assessor_result(hera_result_to_cferp(result, self.task, self.review))
        stored = sorted((a.part, a.effect) for a in self.wf.assessments.values())
        self.assertEqual(stored, [("Valve IV-RB3-17", AssessmentEffect.NOT_RELEVANT),
                                  ("at 11:10", AssessmentEffect.SUPPORTS),
                                  ("was isolated", AssessmentEffect.SUPPORTS)])
        row = board_status({"claims": tuple(self.wf.claims.values()),
                            "assessments": tuple(self.wf.assessments.values())}, origins={})["claims"]["V"]
        self.assertEqual(row["status"], "partly shown")
        self.assertEqual(row["missing_parts"], ["Valve IV-RB3-17"])

        # The Lead records the change and opens a need for the missing part, once.
        changes = [e.payload for e in self.wf.lead.events if e.kind == "claim_status_changed"]
        self.assertEqual([(c["claim_id"], c["from"], c["to"]) for c in changes], [("V", None, "partly shown")])
        need = self.wf.lead.needs["part:V:1"]
        self.assertEqual((need.origin_kind, need.target_ids), ("missing_claim_part", ("V",)))
        self.assertIn('"Valve IV-RB3-17"', need.slots[0].description)
        self.assertNotIn("part:V:2", self.wf.lead.needs)
        self.assertTrue(any(a.role == Role.EVIDENCE_WORKER and a.need_ids == ("part:V:1",)
                            for a in self.wf.assignments.values()))


class StatusView(unittest.TestCase):
    def test_a_passage_supporting_a_claim_and_its_denial_is_flagged(self):
        board = {"claims": [{"claim_id": "UP", "text": "raised"},
                            {"claim_id": "DOWN", "text": "not raised", "denies": ["UP"]}],
                 "assessments": [{"claim_id": c, "material_id": "E05", "passage_id": "p7", "effect": "supports"}
                                 for c in ("UP", "DOWN")]}
        self.assertEqual(board_status(board, origins={})["denial_conflicts"],
                         [{"material_id": "E05", "passage_id": "p7", "claims": ["DOWN", "UP"]}])

    def test_origins_come_from_the_materials_text_when_not_given(self):
        board = {"claims": [{"claim_id": "C", "text": "seepage at closed"}],
                 "materials": [{"material_id": "E08", "content": "Workshop tag VAL-17. Seepage at closed."},
                               {"material_id": "E16", "content": "Prepared from workshop record VAL-17."}],
                 "assessments": [{"claim_id": "C", "material_id": m, "effect": "supports"} for m in ("E08", "E16")]}
        view = board_status(board)
        self.assertEqual(view["origins"], {"E16": "E08"})
        self.assertEqual(view["claims"]["C"]["independent_sources"], 1)


if __name__ == "__main__":
    unittest.main()
