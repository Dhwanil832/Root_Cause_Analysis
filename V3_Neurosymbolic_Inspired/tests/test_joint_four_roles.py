"""One real serial pass through CFERP, SAHS, EWV3, HERA1, then back to CFERP.

Model answers are scripted from the spawned-agent scenario review. The package
engines, ASP solver, validators, adapters, and Lead commit gates are real.
"""
from __future__ import annotations

from dataclasses import replace
import unittest

from cferp import RoleResult
from cferp.contracts import Role
from cferp.integration import (ew_result_to_cferp, hera_result_to_cferp,
                               sahs_result_to_cferp, sahs_sources_from_materials)
from ewv3 import (AnswerSlot, CorpusManifest, EvidenceAssignment, EvidenceWorkerEngine,
                  InformationNeed, InMemoryRetriever, SourceUnit)
from hera1 import AssessmentRoute, Hera1Engine, HeraPipelineAdapter, VersionSnapshot
from sahs.engine import SpecialistEngine
from sahs.engine_contracts import CausalGraph, Proposition
from sahs.history import InMemoryRunHistoryStore
from sahs.solver.clingo_solver import ClingoCandidateSolver
from cferp.workflow import MaterialRecord
from tests.test_cferp_workflow import setup_workflow
from tests.test_hera1 import ScriptedModel
from tests.test_sahs_engine import ScriptedProposer, assignment as sahs_assignment, batch


class Planner:
    def plan_queries(self, assignment):
        return {"queries": [{"slot_id": slot.slot_id,
                             "query": "leaking valve hydraulic pressure loss"}
                            for need in assignment.needs for slot in need.slots]}

    def refine_queries(self, assignment, unresolved_slot_ids, summaries):
        return {"queries": []}

    def draft_requests(self, assignment, unresolved_slot_ids, summaries):
        return {"requests": []}


class CurrentVersions:
    def __init__(self, case_snapshot_id, board_version, material_versions):
        self.snapshot = VersionSnapshot(case_snapshot_id, str(board_version), material_versions)

    def read(self, case_id, material_ids):
        return self.snapshot


class JointFourRoleSmokeTest(unittest.TestCase):
    # Characters of the candidate passage the Assessor leaves out of its quote.
    QUOTE_FROM = 0

    def test_initial_hydraulic_case_returns_neutral_manual_annotation_to_lead(self):
        workflow, lead_specialist = setup_workflow()
        workflow.start_assignment(lead_specialist.assignment_id)

        # Lead constructs the SAHS source bundle from its own catalog IDs.
        base = sahs_assignment()
        sahs_input = replace(
            base,
            assignment_id=lead_specialist.assignment_id,
            case_id="CASE-9",
            case_snapshot_id=lead_specialist.manifest.case_snapshot_id,
            board_version=str(lead_specialist.manifest.board_version),
            history_version="h0",
            history=replace(base.history,
                            case_snapshot_id=lead_specialist.manifest.case_snapshot_id,
                            board_version=str(lead_specialist.manifest.board_version)),
            relevant_graph=CausalGraph((Proposition("H0", "Carrier beam fell", "incident_event", "reported"),)),
            target_proposition_ids=("H0",),
            available_proposition_ids=("H0",),
            source_bundle=sahs_sources_from_materials(lead_specialist.context["source_catalog"]),
            budgets={"max_targeted_expansion_calls": 0},
        )
        agent_answer = batch(information_gaps=[{
            "id": "N1", "question": "Was the valve leaking during the incident?",
            "why_it_matters": "The candidate path requires incident occurrence.",
            "information_that_could_resolve_it": "Incident inspection record.",
            "linked_proposition_ids": ["valve-leaked"], "linked_rule_ids": [],
            "linked_candidate_ids": [], "linked_frontier_ids": [],
        }])
        agent_answer["proposed_rules"][1]["consequent_id"] = "H0"
        source_ref = agent_answer["proposed_rules"][0]["source_refs"][0]
        source_ref.update({"source_id": "DOC-1", "source_version": "v1",
                           "chunk_id": "DOC-1:v1:0"})
        sahs_result = SpecialistEngine(ScriptedProposer([agent_answer]), ClingoCandidateSolver(),
                                       InMemoryRunHistoryStore()).run(sahs_input)
        self.assertTrue(sahs_result.candidates, (sahs_result.status, sahs_result.diagnostics,
                                                  sahs_result.rejected_fragments, sahs_result.open_frontier))

        specialist_packet = sahs_result_to_cferp(sahs_result, lead_specialist)
        worker_assignments = workflow.submit_specialist_result(specialist_packet)
        self.assertIn(sahs_result.candidates[0].candidate_id, workflow.candidate_memberships)
        self.assertTrue(workflow.candidate_memberships[sahs_result.candidates[0].candidate_id][-1].proposition_ids)
        worker_assignment = next(item for item in worker_assignments if item.role == Role.EVIDENCE_WORKER)
        workflow.start_assignment(worker_assignment.assignment_id)

        need = workflow.lead.needs[worker_assignment.need_ids[0]]
        ew_need = InformationNeed(need.need_id, "Investigate the assigned valve-leak condition.", tuple(
            AnswerSlot(slot.slot_id, slot.description, entity_ids=((slot.entity_id,) if slot.entity_id else ()),
                       time_scope=slot.time_scope or "", requested_fields=slot.required_fields)
            for slot in need.slots
        ))
        material = workflow.materials["DOC-1"]
        source = SourceUnit("DOC-1", material.version, "DOC-1:v1:text", material.title,
                            material.content, material.source_kind)
        ew_assignment = EvidenceAssignment(
            "1", worker_assignment.assignment_id, worker_assignment.assignment_id,
            f"ew-event:{worker_assignment.assignment_id}", worker_assignment.manifest.case_id,
            worker_assignment.manifest.case_snapshot_id, str(worker_assignment.manifest.board_version),
            CorpusManifest("CASE-9:corpus:v1", worker_assignment.manifest.material_index_version,
                           "representations:v1", expected_source_ids=("DOC-1",)),
            (ew_need,), (source,), allowed_source_ids=("DOC-1",),
        )
        ew_result = EvidenceWorkerEngine(Planner(), InMemoryRetriever()).run(ew_assignment)
        self.assertEqual(ew_result.status, "ready_for_assessor")
        self.assertTrue(ew_result.slot_results[0].candidate_links)
        worker_packet = ew_result_to_cferp(ew_result, worker_assignment)
        assessor_assignments = workflow.submit_worker_result(worker_packet)
        evidence_assignment = next(item for item in assessor_assignments
                                   if item.context.get("task_kind") == "evidence_review")
        workflow.start_assignment(evidence_assignment.assignment_id)
        # The Assessor's material carries the passage's reading context (title, neighbours).
        routed = evidence_assignment.context["candidate_link"]["passage_context"]
        self.assertIn("readable_text", routed)
        from cferp.integration import hera_task_from_cferp
        hera_material = hera_task_from_cferp(evidence_assignment, workflow).materials[0]
        self.assertEqual(hera_material.location["passage_context"], routed)

        candidate = next(item for item in sahs_result.candidates
                         if "valve-leaked" in item.proposition_ids)
        selected_claim = evidence_assignment.target_ids[0]
        link = ew_result.slot_results[0].candidate_links[0]
        route = AssessmentRoute(
            task_id="hera-joint-task", work_item_id=ew_result.work_item_id,
            event_id=ew_result.event_id, case_id="CASE-9",
            case_snapshot_id=ew_result.case_snapshot_id, board_version=ew_result.board_version,
            specialist_assignment_id=sahs_result.assignment_id,
            specialist_case_snapshot_id=sahs_result.case_snapshot_id,
            specialist_board_version=sahs_result.board_version,
            candidate_id=candidate.candidate_id, need_id=need.need_id,
            slot_ids=(link.slot_id,), worker_id="ew-worker",
            hypothesis_parts=({"part_id": "incident-leak", "board_ids": [selected_claim],
                              "claim_type": "incident_fact",
                              "text": "The valve leaked during this incident."},),
        )
        hera_task = HeraPipelineAdapter.evidence_review(sahs_result, ew_result, route)
        material_version = {"DOC-1": material.version}
        statements = {"statements": [{
            "statement_id": "s1", "material_id": link.candidate_link_id,
            "source_id": "DOC-1", "source_version": material.version,
            "representation_id": link.representation_id, "quote": link.exact_text[self.QUOTE_FROM:],
            "start_offset": link.start_offset + self.QUOTE_FROM, "kind": "general_mechanism",
            "modality": "conditional", "scope": "general", "timing": "unspecified",
        }]}
        comparison = {"parts": [{"part_id": "incident-leak", "findings": [{
            "relation": "does_not_address", "statement_ids": ["s1"],
            "rationale": "The manual describes a general mechanism, not a leak during this incident.",
            "inference_bridge": "", "relevance_status": "direct",
            "scope_alignment": "match", "time_alignment": "match",
        }]}]}
        hera_result = Hera1Engine(ScriptedModel([statements, comparison]),
                                 CurrentVersions(ew_result.case_snapshot_id,
                                                 ew_result.board_version, material_version)).run(hera_task)
        self.assertEqual(hera_result.payload["parts"][0]["relation"], "does_not_address")

        lead_assessment = hera_result_to_cferp(hera_result, hera_task, evidence_assignment)
        workflow.submit_assessor_result(lead_assessment)
        stored = next(iter(workflow.assessments.values()))
        self.assertEqual(stored.effect.value, "neutral")
        # The Lead records the passage it assigned; the Assessor's words ride beside it.
        self.assertEqual((stored.exact_text, stored.quote), (link.exact_text, link.exact_text[self.QUOTE_FROM:]))
        self.assertEqual(workflow.claims[selected_claim].incident_status, "hypothetical")

        # A revised source version reopens only the prior claim/source judgment.
        revised_text = "No leak was observed on V-13 during the incident window."
        revised_assignments = workflow.register_material(event_id="DOC-1-v2", material=MaterialRecord(
            "DOC-1", "v2", "hash-v2", "Revised inspection record", "inspection_log",
            related_claim_ids=(selected_claim,), related_need_ids=(need.need_id,), content=revised_text))
        reassess_assignment = next(item for item in revised_assignments
                                   if item.role == Role.ASSESSOR
                                   and item.context.get("task_kind") == "reassessment_triage")
        workflow.start_assignment(reassess_assignment.assignment_id)
        reassess_route = AssessmentRoute(
            task_id="hera-reassessment", work_item_id=reassess_assignment.assignment_id,
            event_id="hera-reassessment-event", case_id="CASE-9",
            case_snapshot_id=reassess_assignment.manifest.case_snapshot_id,
            board_version=str(reassess_assignment.manifest.board_version),
            target_id=selected_claim, prior_assessment_ids=tuple(reassess_assignment.context["prior_assessment_ids"]),
            hypothesis_parts=({"part_id": "incident-leak", "board_ids": [selected_claim],
                              "claim_type": "incident_fact",
                              "text": "The valve leaked during this incident."},),
        )
        reassess_task = HeraPipelineAdapter.reassessment_review(reassess_assignment, reassess_route)
        revised_statement = {"statements": [{
            "statement_id": "s-rev", "material_id": "DOC-1", "source_id": "DOC-1",
            "source_version": "v2", "representation_id": "DOC-1:v2:text",
            "quote": revised_text, "start_offset": 0, "kind": "incident_observation",
            "modality": "reported", "scope": "incident", "timing": "incident_window",
        }]}
        revised_comparison = {"parts": [{"part_id": "incident-leak", "findings": [{
            "relation": "contradicts", "statement_ids": ["s-rev"],
            "rationale": "The revised incident-window record says no leak was observed.",
            "inference_bridge": "This statement directly conflicts with the leak-occurrence claim.",
            "relevance_status": "direct", "scope_alignment": "match", "time_alignment": "match",
        }]}]}
        reassessment_result = Hera1Engine(ScriptedModel([revised_statement, revised_comparison]),
            CurrentVersions(reassess_assignment.manifest.case_snapshot_id,
                            str(reassess_assignment.manifest.board_version), {"DOC-1": "v2"})).run(reassess_task)
        self.assertEqual(reassessment_result.status, "completed", reassessment_result.diagnostics)
        self.assertEqual(reassessment_result.payload["parts"][0]["relation"], "contradicts")
        reassessment_packet = hera_result_to_cferp(reassessment_result, reassess_task, reassess_assignment)
        workflow.submit_assessor_result(reassessment_packet)
        self.assertEqual(workflow.assessments[stored.assessment_id].status, "superseded_by_reassessment")
        current_assessment = next(item for item in workflow.assessments.values()
                                  if item.material_version == "v2")
        self.assertEqual(current_assessment.effect.value, "contradicts")
        self.assertEqual(workflow.claims[selected_claim].incident_status, "hypothetical")


class AssessorQuotesPartOfThePassage(JointFourRoleSmokeTest):
    """An Assessor may quote one part of a passage, such as one cell of a table row."""
    QUOTE_FROM = 2


if __name__ == "__main__":
    unittest.main()
