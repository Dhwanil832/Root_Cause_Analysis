"""Planner adapters, including the supplied archive's model transport."""
from __future__ import annotations

from typing import Any

from .contracts import EvidenceAssignment
from .prompts import GRADE_SYSTEM, QUERY_SYSTEM, REFINE_QUERY_SYSTEM, REQUEST_SYSTEM


class ArchiveEvidencePlanner:
    """Use the archive's configured Evidence Worker model without side effects."""

    def __init__(self, model: Any, audit_sink: Any | None = None) -> None:
        if not callable(getattr(model, "ask", None)):
            raise ValueError("archive Evidence Worker model must provide ask(task, system, payload)")
        self.model = model
        self.audit_sink = audit_sink
        self.calls_made = 0

    def plan_queries(self, assignment: EvidenceAssignment) -> dict[str, Any]:
        payload = {
            "assignment_id": assignment.assignment_id,
            "needs": [{
                "need_id": need.need_id,
                "target_claim": need.target_claim,
                "search_objective": need.search_objective,
                "slots": [{"slot_id": slot.slot_id, "description": slot.description,
                           "slot_kind": slot.slot_kind, "entity_ids": list(slot.entity_ids),
                           "time_scope": slot.time_scope,
                           "exact_constraints": list(slot.exact_constraints)}
                          for slot in need.slots],
                "comparisons": [{
                    "comparison_id": comparison.comparison_id,
                    "comparison_dimension": comparison.comparison_dimension,
                    "alternatives": [{"slot_id": slot_id,
                                      "description": next(s.description for s in need.slots
                                                          if s.slot_id == slot_id)}
                                     for slot_id in comparison.slot_ids],
                } for comparison in need.comparisons],
            } for need in assignment.needs],
            "pending_request_ids": list(assignment.pending_request_ids),
            "pending_requests": [{"request_id": r.request_id,
                                  "request_type": r.request_type,
                                  "slot_ids": list(r.slot_ids),
                                  "request": r.question_or_document}
                                 for r in assignment.pending_requests],
        }
        return self._ask("ewv3_query_plan", QUERY_SYSTEM, payload)

    def draft_requests(self, assignment: EvidenceAssignment, unresolved_slot_ids: tuple[str, ...],
                       slot_summaries: tuple[dict[str, Any], ...]) -> dict[str, Any]:
        slot_map = {slot.slot_id: slot for need in assignment.needs for slot in need.slots}
        payload = {
            "assignment_id": assignment.assignment_id,
            "unresolved_slots": [{
                "slot_id": sid, "description": slot_map[sid].description,
                "slot_kind": slot_map[sid].slot_kind,
                "entity_ids": list(slot_map[sid].entity_ids),
                "time_scope": slot_map[sid].time_scope,
                "requested_fields": list(slot_map[sid].requested_fields),
            } for sid in unresolved_slot_ids],
            "search_summary": list(slot_summaries),
            "pending_request_ids": list(assignment.pending_request_ids),
            "pending_requests": [{"request_id": r.request_id,
                                  "request_type": r.request_type,
                                  "slot_ids": list(r.slot_ids),
                                  "request": r.question_or_document}
                                 for r in assignment.pending_requests],
        }
        return self._ask("ewv3_request_drafts", REQUEST_SYSTEM, payload)

    def refine_queries(self, assignment: EvidenceAssignment,
                       unresolved_slot_ids: tuple[str, ...],
                       slot_summaries: tuple[dict[str, Any], ...]) -> dict[str, Any]:
        payload = {
            "assignment_id": assignment.assignment_id,
            "unresolved_slots": list(unresolved_slot_ids),
            "first_pass_feedback": list(slot_summaries),
            "comparison_context": [{
                "comparison_id": comparison.comparison_id,
                "comparison_dimension": comparison.comparison_dimension,
                "alternatives": [{"slot_id": slot_id,
                                  "description": next(s.description for s in need.slots
                                                      if s.slot_id == slot_id)}
                                 for slot_id in comparison.slot_ids
                                  if slot_id in unresolved_slot_ids],
            } for need in assignment.needs for comparison in need.comparisons
              if set(comparison.slot_ids).intersection(unresolved_slot_ids)],
        }
        return self._ask("ewv3_query_refinement", REFINE_QUERY_SYSTEM, payload)

    def grade_candidates(self, assignment: EvidenceAssignment,
                         slot_rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
        """One call per slot: the question and its candidate passages with their reading context."""
        payload = {"assignment_id": assignment.assignment_id, "slots": list(slot_rows)}
        return self._ask("ewv3_grade_candidates", GRADE_SYSTEM, payload)

    def _ask(self, task: str, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        before = len(getattr(self.model, "calls", ()))
        result = self.model.ask(task, system, payload)
        self.calls_made += 1
        if self.audit_sink is not None and len(getattr(self.model, "calls", ())) > before:
            record = self.model.calls[-1]
            if hasattr(self.audit_sink, "model_calls"):
                self.audit_sink.model_calls.append(record)
            if hasattr(self.audit_sink, "model_input_history"):
                self.audit_sink.model_input_history.append({
                    "role": "evidence_worker_v3",
                    "task": task,
                    "payload": payload,
                    "model": getattr(record, "model", "unknown"),
                    "actual_provider_completion": getattr(record, "actual_call_performed", None),
                })
        return result

