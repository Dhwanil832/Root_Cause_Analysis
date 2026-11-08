"""Duck-typed boundary adapters for standalone SAHS and EWV3 outputs.

No SAHS/EWV3 imports are required. Lead routing metadata is explicit because
the Lead, not either worker, decides which candidate/need is being assessed.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .contracts import AssessmentRoute, AssessmentTask, EvidenceMaterial


class PipelineAdapterError(ValueError):
    pass


def _get(obj: Any, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _route_dict(route: AssessmentRoute | dict) -> dict:
    if isinstance(route, AssessmentRoute):
        return asdict(route)
    if isinstance(route, dict):
        return route
    raise PipelineAdapterError("route must be an AssessmentRoute or mapping")


def _require_route_fields(route: dict, fields: tuple[str, ...]) -> None:
    for key in fields:
        if not isinstance(route.get(key), str) or not route[key]:
            raise PipelineAdapterError(f"Lead route is missing required {key}")


def _check_versions(specialist_result: Any | None, worker_result: Any | None, route: dict) -> None:
    expected_case = route["case_snapshot_id"]
    expected_board = route["board_version"]
    if specialist_result is not None:
        expected_specialist_case = route.get("specialist_case_snapshot_id") or expected_case
        if _get(specialist_result, "case_snapshot_id") != expected_specialist_case:
            raise PipelineAdapterError("SAHS result case snapshot does not match its Lead assignment")
        expected_specialist_board = route.get("specialist_board_version") or expected_board
        if _get(specialist_result, "board_version") != expected_specialist_board:
            raise PipelineAdapterError("SAHS result board version does not match its Lead assignment")
        expected_assignment = route.get("specialist_assignment_id")
        if not isinstance(expected_assignment, str) or not expected_assignment:
            raise PipelineAdapterError("Lead route is missing specialist_assignment_id")
        if _get(specialist_result, "assignment_id") != expected_assignment:
            raise PipelineAdapterError("SAHS assignment_id does not match Lead route")
    if worker_result is not None:
        if _get(worker_result, "case_snapshot_id") != expected_case:
            raise PipelineAdapterError("EWV3 result case snapshot does not match Lead route")
        if _get(worker_result, "board_version") != expected_board:
            raise PipelineAdapterError("EWV3 result board version does not match Lead route")
    if worker_result is not None:
        for key in ("work_item_id", "event_id"):
            actual = _get(worker_result, key)
            expected = route.get(key)
            if not isinstance(actual, str) or not actual:
                raise PipelineAdapterError(f"EWV3 result is missing {key}")
            if actual != expected:
                raise PipelineAdapterError(f"EWV3 result {key} does not match Lead route")


def _find_candidate(specialist_result: Any, candidate_id: str) -> Any:
    candidates = _get(specialist_result, "candidates", ()) or ()
    matches = [candidate for candidate in candidates if _get(candidate, "candidate_id") == candidate_id]
    if len(matches) > 1:
        raise PipelineAdapterError("SAHS result contains duplicate candidate_id values")
    if matches:
        return matches[0]
    raise PipelineAdapterError("Lead-selected candidate is absent from SAHS result")


def _candidate_links(worker_result: Any, need_id: str, slot_ids: tuple[str, ...]) -> list[Any]:
    links: list[Any] = []
    for slot in (_get(worker_result, "slot_results", ()) or ()):
        if _get(slot, "need_id") != need_id:
            continue
        if slot_ids and _get(slot, "slot_id") not in slot_ids:
            continue
        for link in (_get(slot, "candidate_links", ()) or ()):
            if _get(link, "need_id") != need_id or _get(link, "slot_id") != _get(slot, "slot_id"):
                raise PipelineAdapterError("nested EWV3 candidate link does not match its need/slot result")
            links.append(link)
    # EWV3 may preserve prior hits separately. Include only the assigned need/slots.
    for link in (_get(worker_result, "preserved_candidate_links", ()) or ()):
        if _get(link, "need_id") == need_id and (not slot_ids or _get(link, "slot_id") in slot_ids):
            links.append(link)
    unique = {}
    for link in links:
        link_id = _get(link, "candidate_link_id")
        if not isinstance(link_id, str) or not link_id:
            raise PipelineAdapterError("EWV3 candidate link lacks candidate_link_id")
        existing = unique.get(link_id)
        if existing is not None:
            identity_fields = ("need_id", "slot_id", "source_id", "source_version", "representation_id",
                               "start_offset", "end_offset", "exact_text")
            if any(_get(existing, field) != _get(link, field) for field in identity_fields):
                raise PipelineAdapterError("duplicate EWV3 candidate_link_id has conflicting provenance/content")
            continue
        unique[link_id] = link
    return list(unique.values())


def _require_assessor_ready(worker_result: Any) -> None:
    if _get(worker_result, "status") != "ready_for_assessor":
        raise PipelineAdapterError("EWV3 result is not ready for Assessor review")
    phase = _get(worker_result, "work_phase")
    if phase is None or str(phase) not in {"awaiting_assessor", "WorkPhase.AWAITING_ASSESSOR"}:
        raise PipelineAdapterError("EWV3 work phase is inconsistent with assessor readiness")


def _materials(links: list[Any]) -> tuple[EvidenceMaterial, ...]:
    out = []
    for link in links:
        quote = _get(link, "exact_text")
        if not isinstance(quote, str) or not quote.strip():
            continue
        start = _get(link, "start_offset")
        out.append(EvidenceMaterial(
            material_id=str(_get(link, "candidate_link_id")),
            source_id=str(_get(link, "source_id")),
            source_version=str(_get(link, "source_version")),
            representation_id=str(_get(link, "representation_id")),
            text=quote,
            source_kind=str(_get(link, "source_kind", "document")),
            offset_base=start if type(start) is int and start >= 0 else 0,
            location={
                "title": _get(link, "title", ""),
                "start_offset_missing": not (type(start) is int and start >= 0),
                "candidate_link_id": _get(link, "candidate_link_id"),
                "need_id": _get(link, "need_id"),
                "slot_id": _get(link, "slot_id"),
                "structural_context": _get(link, "structural_context", {}),
                "retrieval_score_semantics": _get(link, "score_semantics", "retrieval_rank_only"),
            },
        ))
    return tuple(out)


def _unassessable_links(links: list[Any]) -> list[dict[str, Any]]:
    return [{"candidate_link_id": _get(link, "candidate_link_id"),
             "source_id": _get(link, "source_id"),
             "source_version": _get(link, "source_version"),
             "representation_id": _get(link, "representation_id"),
             "modality": _get(link, "modality", "unknown"),
             "location": _get(link, "structural_context", {})}
            for link in links if not isinstance(_get(link, "exact_text"), str)
            or not _get(link, "exact_text", "").strip()]


class HeraPipelineAdapter:
    """Translate SAHS/EWV3 results plus Lead routing into a HERA task."""

    @staticmethod
    def evidence_review(specialist_result: Any, worker_result: Any,
                        route: AssessmentRoute | dict) -> AssessmentTask:
        route = _route_dict(route)
        _require_route_fields(route, ("task_id", "work_item_id", "event_id", "case_id",
            "case_snapshot_id", "board_version", "candidate_id", "need_id", "worker_id",
            "specialist_assignment_id"))
        _check_versions(specialist_result, worker_result, route)
        _require_assessor_ready(worker_result)
        candidate_id = route.get("candidate_id")
        need_id = route.get("need_id")
        if not candidate_id or not need_id:
            raise PipelineAdapterError("Lead route must name candidate_id and need_id")
        candidate = _find_candidate(specialist_result, candidate_id)
        slot_ids = tuple(route.get("slot_ids", ()))
        links = _candidate_links(worker_result, need_id, slot_ids)
        materials = _materials(links)
        parts = route.get("hypothesis_parts")
        if not isinstance(parts, (list, tuple)) or not parts:
            raise PipelineAdapterError("Lead route must provide selected hypothesis_parts")
        candidate_node_ids = set(_get(candidate, "proposition_ids", ()) or ()) | set(_get(candidate, "rule_ids", ()) or ())
        for part in parts:
            if not isinstance(part, dict):
                raise PipelineAdapterError("hypothesis_parts must be mappings")
            part_node_ids = part.get("board_ids")
            if (not isinstance(part_node_ids, (list, tuple)) or not part_node_ids
                    or any(not isinstance(node_id, str) or not node_id for node_id in part_node_ids)
                    or not set(part_node_ids).issubset(candidate_node_ids)):
                raise PipelineAdapterError("each hypothesis part must name board_ids from the selected SAHS candidate")
        return AssessmentTask(
            schema_version="1", task_id=route["task_id"],
            work_item_id=route["work_item_id"], event_id=route["event_id"],
            case_id=route["case_id"], case_snapshot_id=route["case_snapshot_id"],
            board_version=route["board_version"], task_kind="evidence_review",
            sender_role="evidence_worker", sender_id=route["worker_id"],
            materials=materials,
            hypothesis={"hypothesis_id": candidate_id,
                        "candidate_summary": {
                            "proposition_ids": list(_get(candidate, "proposition_ids", ()) or ()),
                            "rule_ids": list(_get(candidate, "rule_ids", ()) or ()),
                            "assumptions": list(_get(candidate, "assumptions", ()) or ()),
                        },
                        "parts": list(parts)},
            context={"need_id": need_id, "slot_ids": list(slot_ids),
                     "worker_status": _get(worker_result, "status"),
                     "search_pass_status": str(_get(worker_result, "search_pass_status", "unknown")),
                     "worker_diagnostics": list(_get(worker_result, "diagnostics", ()) or ()),
                     "unassessable_materials": _unassessable_links(links),
                     "retrieval_is_not_assessment": True},
        )

    @staticmethod
    def request_review(worker_result: Any, route: AssessmentRoute | dict) -> AssessmentTask:
        route = _route_dict(route)
        _require_route_fields(route, ("task_id", "work_item_id", "event_id", "case_id",
            "case_snapshot_id", "board_version", "request_id", "target_id", "worker_id"))
        _check_versions(None, worker_result, route)
        _require_assessor_ready(worker_result)
        request_id = route.get("request_id")
        draft = next((item for item in (_get(worker_result, "request_drafts", ()) or ())
                      if _get(item, "request_id") == request_id), None)
        if draft is None:
            raise PipelineAdapterError("Lead-selected request is absent from EWV3 output")
        req_type = _get(draft, "request_type")
        if req_type not in {"terminology_question", "incident_question", "document_request"}:
            raise PipelineAdapterError("EWV3 request draft has unsupported request_type")
        draft_slot_ids = set(_get(draft, "slot_ids", ()) or ())
        route_slot_ids = set(route.get("slot_ids", ()))
        if not draft_slot_ids or not route_slot_ids or not draft_slot_ids.intersection(route_slot_ids):
            raise PipelineAdapterError("EWV3 request draft does not overlap the Lead-selected slots")
        request_history = []
        for prior in route.get("request_history", ()):
            prior_type = _get(prior, "request_type", _get(prior, "kind", ""))
            prior_text = _get(prior, "question_or_document", _get(prior, "text", ""))
            request_history.append({
                "target_id": _get(prior, "target_id", route["target_id"]),
                "kind": "document_request" if prior_type == "document_request" else "question",
                "request_type": prior_type,
                "text": prior_text,
            })
        existing_links = (_candidate_links(worker_result, route["need_id"], tuple(route.get("slot_ids", ())))
                          if route.get("need_id") else [])
        selected_slot_ids = set(route.get("slot_ids", ()))
        coverage = [
            {"slot_id": _get(slot, "slot_id"), "coverage": str(_get(slot, "coverage", "unknown"))}
            for slot in (_get(worker_result, "slot_results", ()) or ())
            if _get(slot, "need_id") == route.get("need_id")
            and (not selected_slot_ids or _get(slot, "slot_id") in selected_slot_ids)
        ][:24]
        return AssessmentTask(
            schema_version="1", task_id=route["task_id"],
            work_item_id=route["work_item_id"], event_id=route["event_id"],
            case_id=route["case_id"], case_snapshot_id=route["case_snapshot_id"],
            board_version=route["board_version"], task_kind="request_review",
            sender_role="evidence_worker", sender_id=route["worker_id"],
            request={"request_id": request_id,
                     "target_id": route["target_id"],
                     "kind": "document_request" if req_type == "document_request" else "question",
                     "request_type": req_type,
                     "text": _get(draft, "question_or_document", ""),
                     "slot_ids": list(_get(draft, "slot_ids", ())),
                     "requested_fields": list(_get(draft, "requested_fields", ())),
                     "why_it_may_help": _get(draft, "why_it_may_help", "")},
            request_history=tuple(request_history),
            context={"target_description": route.get("target_description", ""),
                     "open_gap": route.get("open_gap", ""),
                     "search_pass_status": str(_get(worker_result, "search_pass_status", "unknown")),
                     "slot_coverage": coverage,
                     "diagnostics": [str(item)[:300] for item in (_get(worker_result, "diagnostics", ()) or ())[:5]],
                     "searched_source_ids": sorted({
                         source_id
                         for trace in (_get(worker_result, "traces", ()) or ())
                         for source_id in (_get(trace, "source_ids_searched", ()) or ())
                     })[:50],
                     "existing_candidate_links": [
                         {"candidate_link_id": _get(link, "candidate_link_id"),
                          "source_id": _get(link, "source_id"),
                          "slot_id": _get(link, "slot_id"),
                          "exact_text": str(_get(link, "exact_text", ""))[:350]}
                         for link in existing_links[:8]
                     ]},
            revision_attempt=int(route.get("revision_attempt", 0)),
        )

    @staticmethod
    def clarification_review(specialist_result: Any, route: AssessmentRoute | dict,
                             answer: dict, worker_result: Any | None = None) -> AssessmentTask:
        route = _route_dict(route)
        if not isinstance(answer, dict):
            raise PipelineAdapterError("answer must be a mapping")
        for key in ("task_id", "work_item_id", "event_id", "case_id", "case_snapshot_id",
                    "board_version", "clarification_id"):
            if not isinstance(route.get(key), str) or not route[key]:
                raise PipelineAdapterError(f"route is missing required {key}")
        _check_versions(specialist_result, worker_result, route)
        clarification_id = route.get("clarification_id")
        item = next((x for x in (_get(specialist_result, "clarification_items", ()) or ())
                     if _get(x, "clarification_id") == clarification_id), None)
        if item is None:
            raise PipelineAdapterError("Lead-selected clarification is absent from SAHS result")
        materials = ()
        unassessable = []
        if answer.get("kind") == "document":
            if worker_result is None:
                raise PipelineAdapterError("document answer requires EWV3-linked material")
            if not isinstance(route.get("need_id"), str) or not route["need_id"]:
                raise PipelineAdapterError("document clarification route requires need_id")
            _require_assessor_ready(worker_result)
            links = _candidate_links(worker_result, route["need_id"], tuple(route.get("slot_ids", ())))
            materials = _materials(links)
            unassessable = _unassessable_links(links)
        prior_answers = route.get("prior_answers", ())
        if not isinstance(prior_answers, (list, tuple)):
            raise PipelineAdapterError("prior_answers must be an array")
        if any(not isinstance(row, dict) or row.get("question_id") != clarification_id for row in prior_answers):
            raise PipelineAdapterError("prior answer does not match the assigned clarification_id")
        answer = dict(answer)
        if answer.get("question_id") not in (None, clarification_id):
            raise PipelineAdapterError("answer question_id conflicts with the Lead-routed clarification")
        # Intake answer records often carry only their response type and content;
        # bind them to the exact question selected by the Lead at this boundary.
        answer["question_id"] = clarification_id
        return AssessmentTask(
            schema_version="1", task_id=route["task_id"],
            work_item_id=route["work_item_id"], event_id=route["event_id"],
            case_id=route["case_id"], case_snapshot_id=route["case_snapshot_id"],
            board_version=route["board_version"], task_kind="clarification_review",
            sender_role=route.get("sender_role", "lead"),
            sender_id=route.get("sender_id", "lead"), materials=materials,
            clarification={"question_id": clarification_id,
                           "text": _get(item, "question", ""),
                           "why_it_matters": _get(item, "why_it_matters", "")},
            answer=answer, prior_answers=tuple(prior_answers),
            context={"unassessable_materials": unassessable},
        )

    @staticmethod
    def reassessment_review(assignment: Any, route: AssessmentRoute | dict) -> AssessmentTask:
        """Build HERA's source-revision review from a CFERP reassessment job."""
        route = _route_dict(route)
        _require_route_fields(route, ("task_id", "work_item_id", "event_id", "case_id",
            "case_snapshot_id", "board_version", "target_id"))
        # Avoid importing CFERP into HERA; accept its string enum at the boundary.
        if str(_get(assignment, "role")) not in {"assessor", "Role.ASSESSOR"}:
            raise PipelineAdapterError("reassessment route must come from a Lead Assessor assignment")
        if _get(assignment, "assignment_id") != route.get("work_item_id"):
            raise PipelineAdapterError("reassessment task must preserve the Lead assignment ID")
        manifest = _get(assignment, "manifest")
        if (_get(manifest, "case_snapshot_id") != route["case_snapshot_id"]
                or str(_get(manifest, "board_version")) != str(route["board_version"])
                or _get(manifest, "case_id") != route["case_id"]):
            raise PipelineAdapterError("reassessment route is stale against the Lead assignment")
        target_id = route["target_id"]
        if target_id not in (_get(assignment, "target_ids", ()) or ()):
            raise PipelineAdapterError("reassessment target is outside the Lead assignment")
        expected_prior = tuple(_get(assignment, "context", {}).get("prior_assessment_ids", ()))
        prior_ids = tuple(route.get("prior_assessment_ids", ()))
        if not expected_prior or set(prior_ids) != set(expected_prior):
            raise PipelineAdapterError("reassessment prior assessment IDs differ from the Lead assignment")
        material = _get(assignment, "context", {}).get("material")
        if material is None:
            raise PipelineAdapterError("reassessment Lead assignment has no revised material")
        content = _get(material, "content")
        material_id = _get(material, "material_id")
        version = _get(material, "version")
        materials = ()
        unassessable = []
        if isinstance(content, str) and content.strip():
            materials = (EvidenceMaterial(
                str(material_id), str(material_id), str(version),
                f"{material_id}:{version}:text", content,
                str(_get(material, "source_kind", "document")), 0,
                {"title": _get(material, "title", ""), "reassessment": True},
            ),)
        else:
            unassessable = [{"source_id": str(material_id), "source_version": str(version),
                             "representation_id": f"{material_id}:{version}:text"}]
        parts = route.get("hypothesis_parts")
        if not isinstance(parts, (list, tuple)) or not parts:
            raise PipelineAdapterError("reassessment route must provide the exact hypothesis part")
        if any(not isinstance(part, dict) or target_id not in (part.get("board_ids") or ())
               for part in parts):
            raise PipelineAdapterError("reassessment hypothesis part must include the routed target")
        return AssessmentTask(
            schema_version="1", task_id=route["task_id"],
            work_item_id=route["work_item_id"], event_id=route["event_id"],
            case_id=route["case_id"], case_snapshot_id=route["case_snapshot_id"],
            board_version=route["board_version"], task_kind="reassessment_triage",
            sender_role="lead", sender_id=route.get("sender_id") or "lead",
            materials=materials,
            hypothesis={"hypothesis_id": target_id, "parts": list(parts)},
            prior_assessment_ids=prior_ids,
            context={"prior_assessment_ids": list(prior_ids),
                     "prior_assessments": [asdict(item) if hasattr(item, "__dataclass_fields__") else item
                                            for item in _get(assignment, "context", {}).get("prior_assessments", ())],
                     "unassessable_materials": unassessable},
        )
