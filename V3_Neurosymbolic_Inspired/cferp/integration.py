"""Explicit Lead-owned adapters between the standalone V3 packages and CFERP.

These helpers normalize package results into CFERP's immutable ``RoleResult``
contract. They do not decide which hypothesis or request the Lead should route.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Iterable

from sahs.engine_contracts import SourceChunk

from .contracts import Role
from .workflow import Assignment, RoleResult


class IntegrationError(ValueError):
    pass


# A request review sees at most this many retrieved passages, each cut to this
# length: the bounds hera1.pipeline_adapter applies, so HERA's max_context_chars
# holds however many links retrieval has accumulated for the request's needs.
MAX_REVIEW_LINKS = 8
MAX_REVIEW_LINK_CHARS = 350


def sahs_sources_from_materials(materials: Iterable[Any]) -> tuple[SourceChunk, ...]:
    """Use CFERP material IDs as SAHS source IDs, preserving each version."""
    chunks = []
    for item in materials:
        material_id = _get(item, "material_id")
        version = _get(item, "version")
        content = _get(item, "content")
        if not all(isinstance(x, str) and x for x in (material_id, version)):
            raise IntegrationError("material needs stable material_id and version")
        if not isinstance(content, str):
            continue
        chunks.append(SourceChunk(material_id, version, f"{material_id}:{version}:0",
                                  content, str(_get(item, "source_kind", "case_document"))))
    return tuple(chunks)


# The Specialist reads Assessor annotations as reading notes: which passage was
# judged, how, and why. The Lead's bookkeeping (version manifests, content
# hashes, job IDs) stays on the board; sent along it made each annotation about
# 3 KB of hash-heavy text and pushed late Specialist prompts past the context.
MAX_SPECIALIST_ANNOTATIONS = 12
MAX_ANNOTATION_RATIONALE_CHARS = 400


def specialist_annotations(annotations: Iterable[Any]) -> tuple[dict[str, Any], ...]:
    """Current annotations in compact form: evidence-bearing effects first, then newest."""
    rows = [a for a in annotations if str(_get(a, "status", "current")) == "current"]
    ranked = sorted(enumerate(rows), key=lambda pair: (
        str(_get(pair[1], "effect", "")) in {"neutral", "rejected_link"}, -pair[0]))
    kept = sorted(ranked[:MAX_SPECIALIST_ANNOTATIONS], key=lambda pair: pair[0])
    return tuple({
        "annotation_id": str(_get(a, "assessment_id", "")),
        "target_id": str(_get(a, "claim_id", "")),
        "material_id": str(_get(a, "material_id", "")),
        "exact_text": str(_get(a, "exact_text", "")),
        "effect": str(_get(a, "effect", "")),
        "rationale": str(_get(a, "rationale", ""))[:MAX_ANNOTATION_RATIONALE_CHARS],
    } for _, a in kept)


def sahs_assignment_from_cferp(assignment: Assignment, workflow: Any, *,
                               history: Any | None = None,
                               budgets: dict[str, Any] | None = None) -> Any:
    """Build a standalone SAHS assignment from a Lead-owned assignment.

    SAHS remains independent of CFERP; this adapter is the explicit boundary.
    Existing CFERP claims/links are converted to a read-only graph snapshot.
    """
    if assignment.role != Role.SPECIALIST:
        raise IntegrationError("SAHS input requires a Specialist Lead assignment")
    from sahs.contracts import SpecialistHistory
    from sahs.engine_contracts import (CausalGraph, CausalRuleCandidate, Proposition,
                                       SourceReference, SpecialistAssignment)

    context = assignment.context
    scope_id = str(context.get("specialist_profile_id") or assignment.owner_id or "lead-routed")
    if history is None:
        history = SpecialistHistory("1", scope_id, "h0", assignment.manifest.case_snapshot_id,
                                    str(assignment.manifest.board_version))
    if (history.case_snapshot_id != assignment.manifest.case_snapshot_id
            or str(history.board_version) != str(assignment.manifest.board_version)):
        raise IntegrationError("SAHS history snapshot differs from the Lead assignment")
    mode = str(context.get("mode", "revision" if assignment.target_ids else "initial"))
    if mode not in {"initial", "revision", "advance"}:
        mode = "revision" if assignment.target_ids else "initial"
    props = tuple(Proposition(c.claim_id, c.text,
        c.kind if c.kind in {"case_claim", "incident_event", "component_state", "system_mechanism",
                             "unknown_term", "unknown_condition"} else "case_claim",
        c.incident_status if c.incident_status in {"reported", "hypothetical", "unresolved", "not_applicable"}
        else "unresolved", time_scope=None)
        for c in workflow.claims.values())
    rules = []
    for link in workflow.causal_links.values():
        refs = []
        for source_id in link.source_refs:
            material = workflow.materials.get(source_id)
            if material and link.source_text and material.content and link.source_text in material.content:
                start = material.content.find(link.source_text)
                refs.append(SourceReference(source_id, material.version, f"{source_id}:{material.version}:0",
                    link.source_text, start, start + len(link.source_text), material.source_kind,
                    link.source_relation))
        rules.append(CausalRuleCandidate(link.link_id, link.source_claim_ids, link.target_claim_id,
            link.relation, link.modality, link.conditions, link.time_constraint, link.basis,
            tuple(refs), link.source_relation, link.status))
    graph = CausalGraph(props, tuple(rules))
    focal = assignment.target_ids[0] if assignment.target_ids else None
    return SpecialistAssignment(
        schema_version="1", assignment_id=assignment.assignment_id, case_id=assignment.manifest.case_id,
        specialist_scope_id=scope_id, case_snapshot_id=assignment.manifest.case_snapshot_id,
        board_version=str(assignment.manifest.board_version), history_version=history.history_version,
        mode=mode, operation_goal=str(context.get("operation_goal") or assignment.purpose),
        lead_direction={"purpose": assignment.purpose, **{
            k: v for k, v in context.items() if k in {"mode", "lead_feedback", "direction", "focal_proposition_id"}}},
        relevant_graph=graph,
        source_bundle=sahs_sources_from_materials(context.get("source_catalog", workflow.materials.values())),
        history=history, focal_proposition_id=(context.get("focal_proposition_id") or focal
            if mode in {"revision", "advance"} else None),
        target_proposition_ids=assignment.target_ids,
        available_proposition_ids=tuple(p.proposition_id for p in props),
        initial_case_packet=context.get("case_packet") if mode == "initial" else None,
        lead_feedback=tuple(context.get("lead_feedback", ())),
        assessor_annotations=specialist_annotations(context.get("assessor_annotations", ())),
        changed_ids=tuple(context.get("changed_ids", ())),
        budgets=dict(budgets or assignment.budget),
    )


def ew_assignment_from_cferp(assignment: Assignment, workflow: Any, *,
                             event_id: str | None = None,
                             representation_version: str = "representations:v1",
                             budgets: dict[str, int] | None = None) -> Any:
    """Build an EWV3 assignment entirely from a Lead work assignment/catalog.

    It carries the Lead's exact targets and need slots, material versions,
    source scope, and any prior packet links. Retrieval ranking is still EWV3's
    job; this adapter only transports the assignment boundary.
    """
    if assignment.role != Role.EVIDENCE_WORKER:
        raise IntegrationError("EWV3 input requires an Evidence Worker Lead assignment")
    from ewv3.contracts import (AnswerSlot, CandidateLink, CorpusManifest, EvidenceAssignment,
                                InformationNeed, RequestDraft, SourceUnit)

    needs = []
    for need_id in assignment.need_ids:
        need = workflow.lead.needs.get(need_id)
        if need is None:
            raise IntegrationError(f"Lead assignment references unknown need {need_id}")
        target_text = " ; ".join(workflow.claims[target].text for target in need.target_ids
                                  if target in workflow.claims)
        if not target_text:
            target_text = assignment.purpose
        slots = tuple(AnswerSlot(slot.slot_id, slot.description,
            slot_kind=slot.record_type or "incident_information",
            entity_ids=(slot.entity_id,) if slot.entity_id else (),
            time_scope=slot.time_scope or "", requested_fields=slot.required_fields)
            for slot in need.slots if slot.state.value in {"open", "in_process"})
        if not slots:
            raise IntegrationError(f"Lead need {need_id} has no open slots")
        needs.append(InformationNeed(need_id, target_text, slots,
            search_objective="candidate_retrieval", branch_id="|".join(
                workflow.claims[target].branch_id for target in need.target_ids if target in workflow.claims)))

    catalog = assignment.context.get("source_catalog", workflow.materials.values())
    allowed_ids: set[str] = set()
    for need_id in assignment.need_ids:
        need = workflow.lead.needs[need_id]
        allowed_ids.update(need.source_scope)
    if "new_material_id" in assignment.context:
        allowed_ids.add(str(assignment.context["new_material_id"]))
    source_records = [item for item in catalog if not allowed_ids or item.material_id in allowed_ids]
    source_records.sort(key=lambda item: item.material_id)
    sources = tuple(SourceUnit(item.material_id, item.version,
        f"{item.material_id}:{item.version}:text", item.title, item.content or "",
        item.source_kind, searchable=item.readiness == "ready", readiness=item.readiness,
        origin=str(item.metadata.get("origin", "")), lineage=item.lineage,
        metadata=dict(item.metadata)) for item in source_records)
    versions = tuple((item.material_id, item.version, item.content_hash) for item in source_records)
    expected = tuple(item.material_id for item in source_records)
    failed = tuple(item.material_id for item in source_records if item.readiness in {"failed", "unreadable"})
    pending = tuple(item.material_id for item in source_records if item.readiness in {"pending", "processing"})
    manifest = CorpusManifest(
        corpus_snapshot_id=f"corpus:{assignment.manifest.case_snapshot_id}:{assignment.manifest.material_index_version}",
        material_catalog_version=assignment.manifest.material_index_version,
        representation_version=representation_version, expected_source_ids=expected,
        failed_source_ids=failed, pending_source_ids=pending)
    prior_link_rows = []
    for need_id in assignment.need_ids:
        packet = workflow.need_packets.get(need_id)
        if packet is not None:
            prior_link_rows.extend((need_id, row) for row in workflow._candidate_links_from_packet(packet))
    prior_links = [CandidateLink(
        str(row.get("passage_id", "")), need_id, str(row.get("slot_id", "")),
        str(row["material_id"]), str(row["material_version"]),
        str(row.get("representation_id", f"{row['material_id']}:{row['material_version']}:text")),
        row.get("start_offset"), row.get("end_offset"), str(row.get("exact_text", "")),
        str(row.get("title", "")), str(row.get("source_kind", "unknown")), "preserved",
        0.0, score_semantics="preserved_prior_candidate")
        for need_id, row in prior_link_rows]
    pending_requests = []
    for request in workflow.lead.requests.values():
        if (set(request.origin_ids).intersection(assignment.need_ids)
                and request.state.value in {"sent", "waiting_response", "partially_answered"}):
            pending_requests.append(RequestDraft(request.request_id, request.request_kind,
                request.slot_ids, request.wording, request.entity_ids, request.time_scope or "",
                request.record_types, why_it_may_help="Lead-approved open request",
                searched_scope=request.source_scope))
    return EvidenceAssignment(
        schema_version="1", assignment_id=assignment.assignment_id,
        work_item_id=assignment.assignment_id,
        event_id=event_id or f"ew-event:{assignment.assignment_id}", case_id=assignment.manifest.case_id,
        case_snapshot_id=assignment.manifest.case_snapshot_id,
        board_version=str(assignment.manifest.board_version), manifest=manifest,
        needs=tuple(needs), sources=sources, allowed_source_ids=expected,
        pending_request_ids=tuple(item.request_id for item in pending_requests),
        pending_requests=tuple(pending_requests), prior_candidate_links=tuple(prior_links),
        assessor_feedback=tuple(assignment.context.get("assessor_feedback", ())),
        budgets=dict(budgets or assignment.budget),
    )


_PASSAGE_CONTEXT_KEYS = ("document_title", "document_details", "section", "readable_text",
                         "before", "after", "passage_kind", "reader_grade", "reader_role")


def _passage_context(structural_context: dict[str, Any]) -> dict[str, Any]:
    """The reading context of a passage (section, neighbours, table columns, grade), never its source map."""
    return {key: structural_context[key] for key in _PASSAGE_CONTEXT_KEYS if key in structural_context}


def hera_task_from_cferp(assignment: Assignment, workflow: Any | None = None) -> Any:
    """Build a HERA task for a single Lead-issued Assessor assignment."""
    if assignment.role != Role.ASSESSOR:
        raise IntegrationError("HERA task requires an Assessor Lead assignment")
    from hera1 import AssessmentTask, EvidenceMaterial
    kind = assignment.context.get("task_kind", "evidence_review")
    base = dict(schema_version="1", task_id=assignment.assignment_id,
        work_item_id=assignment.context.get("source_work_item_id", assignment.assignment_id),
        event_id=f"hera-event:{assignment.assignment_id}",
        case_id=assignment.manifest.case_id, case_snapshot_id=assignment.manifest.case_snapshot_id,
        board_version=str(assignment.manifest.board_version), task_kind=kind,
        sender_role="evidence_worker" if kind in {"evidence_review", "request_review"} else "lead",
        sender_id=assignment.owner_id)
    if kind == "evidence_review":
        link = assignment.context.get("candidate_link")
        claim = assignment.context.get("claim")
        material = assignment.context.get("material")
        if not isinstance(link, dict) or claim is None or material is None:
            raise IntegrationError("evidence review assignment lacks its claim, passage, or material")
        evidence = EvidenceMaterial(str(link["passage_id"]), str(link["material_id"]),
            str(link["material_version"]), str(link.get("representation_id") or
            f"{link['material_id']}:{link['material_version']}:text"), str(link["exact_text"]),
            str(link.get("source_kind", material.source_kind)),
            link.get("start_offset") if type(link.get("start_offset")) is int else 0,
            {"title": material.title, "need_ids": list(link.get("need_ids", ())),
             "slot_id": link.get("slot_id"),
             **({"passage_context": dict(link["passage_context"])} if link.get("passage_context") else {})})
        cferp_claim_kind = str(getattr(claim, "kind", "other"))
        hera_claim_type = {
            "incident_event": "incident_fact",
            "incident_causal_link": "incident_causal_link",
            "causal_link": "incident_causal_link",
            "system_mechanism": "general_mechanism",
            "general_mechanism": "general_mechanism",
        }.get(cferp_claim_kind, "other")
        hypothesis = {"hypothesis_id": str(link["claim_id"]), "parts": [{
            "part_id": f"claim:{claim.claim_id}", "board_ids": [claim.claim_id],
            "claim_type": hera_claim_type,
            "text": claim.text}]}
        return AssessmentTask(**base, materials=(evidence,), hypothesis=hypothesis,
            context={"task_kind": kind, "claim_id": claim.claim_id,
                     "candidate_link": dict(link), "packet_id": assignment.context.get("packet_id")})
    if kind == "reassessment_triage":
        material = assignment.context.get("material")
        prior = tuple(assignment.context.get("prior_assessments", ()))
        if material is None or not prior:
            raise IntegrationError("reassessment assignment lacks revised material or prior assessments")
        evidence = EvidenceMaterial(material.material_id, material.material_id, material.version,
            f"{material.material_id}:{material.version}:text", material.content or "",
            material.source_kind, 0, {"title": material.title, "reassessment": True})
        claim_id = assignment.target_ids[0]
        claim_text = (workflow.claims[claim_id].text if workflow is not None and claim_id in workflow.claims
                      else str(assignment.context.get("claim_text", claim_id)))
        from dataclasses import asdict, is_dataclass
        return AssessmentTask(**base, materials=(evidence,), hypothesis={"hypothesis_id": claim_id,
            "parts": [{"part_id": f"claim:{claim_id}", "board_ids": [claim_id],
                       "claim_type": "incident_fact", "text": claim_text}]},
            prior_assessment_ids=tuple(assignment.context["prior_assessment_ids"]),
            context={"prior_assessment_ids": list(assignment.context["prior_assessment_ids"]),
                     "prior_assessments": [dict(item) if isinstance(item, dict) else asdict(item)
                                            for item in prior if isinstance(item, dict) or is_dataclass(item)]})
    if kind == "request_review":
        request = assignment.context.get("request")
        if request is None:
            raise IntegrationError("request review assignment has no Lead request")
        request_kind = "document_request" if request.request_kind == "document_request" else "question"
        found = [row for row in assignment.context.get("existing_candidate_links", ()) if isinstance(row, dict)]
        shown = [{"candidate_link_id": row.get("candidate_link_id"), "source_id": row.get("source_id"),
                  "slot_id": row.get("slot_id"),
                  "exact_text": str(row.get("exact_text", ""))[:MAX_REVIEW_LINK_CHARS]}
                 for row in found[:MAX_REVIEW_LINKS]]
        link_context = {"existing_candidate_links": shown}
        if len(found) > len(shown):
            link_context["omitted_candidate_link_count"] = len(found) - len(shown)
        return AssessmentTask(**base, request={"request_id": request.request_id,
            "target_id": request.target_ids[0] if request.target_ids else "",
            "kind": request_kind, "request_type": request_kind,
            "text": request.wording, "slot_ids": list(request.slot_ids),
            "requested_fields": list(request.record_types), "why_it_may_help": ""},
            context={"task_kind": kind, "request_id": request.request_id,
                     "origin_ids": list(request.origin_ids), "request_version": request.request_version,
                     **link_context})
    if kind == "clarification_review":
        answer = assignment.context.get("clarification")
        if answer is None:
            raise IntegrationError("clarification review assignment has no routed answer")
        need = assignment.context.get("need")
        if need is None and workflow is not None:
            need = workflow.lead.needs.get(answer.need_id)
        question = ""
        if need is not None:
            question = " ".join(slot.description for slot in need.slots)
        answer_kind = "document" if answer.source_material_ids else "human"
        materials = []
        unassessable = []
        for material_id in answer.source_material_ids:
            material = workflow.materials.get(material_id) if workflow is not None else None
            if material is None or not material.content:
                unassessable.append({"source_id": material_id,
                                     "reason": "no searchable text supplied to HERA"})
                continue
            materials.append(EvidenceMaterial(material.material_id, material.material_id,
                material.version, f"{material.material_id}:{material.version}:text",
                material.content, material.source_kind, 0, {"title": material.title}))
        answer_data = {"question_id": answer.clarification_id, "answer_id": answer.answer_id,
            "kind": answer_kind, "text": answer.answer_text}
        return AssessmentTask(**base, clarification={"question_id": answer.clarification_id,
            "text": question, "why_it_matters": "Clarification routed by the Lead."},
            answer=answer_data, materials=tuple(materials),
            context={"task_kind": kind, "need_id": answer.need_id,
                     "unassessable_materials": unassessable})
    raise IntegrationError(f"automated HERA builder does not yet support task kind {kind}")


def sahs_result_to_cferp(result: Any, assignment: Assignment,
                         *, result_id: str | None = None) -> RoleResult:
    """Normalize an SAHS delta for the Lead's CFERP commit gate.

    Source IDs must already be CFERP material IDs; ``sahs_sources_from_materials``
    creates that contract at assignment construction time. Candidate operations
    are intentionally not auto-applied: branch activation and merge decisions
    remain Lead actions.
    """
    if _get(result, "assignment_id") != assignment.assignment_id:
        raise IntegrationError("SAHS result does not match its Lead assignment ID")
    if (_get(result, "case_snapshot_id") != assignment.manifest.case_snapshot_id
            or str(_get(result, "board_version")) != str(assignment.manifest.board_version)):
        raise IntegrationError("SAHS result does not match its Lead assignment snapshot")
    status = _get(result, "status")
    if status not in {"completed", "open_frontier", "partial_budget", "no_candidate_under_supplied_rules", "no_op"}:
        raise IntegrationError(f"SAHS result is not commit-ready: {status}")

    graph = _get(result, "graph_delta")
    props = _get(graph, "propositions", ()) or ()
    rules = _get(graph, "rules", ()) or ()
    candidates = _get(result, "candidates", ()) or ()
    memberships: dict[str, list[str]] = {}
    for candidate in candidates:
        candidate_id = _get(candidate, "candidate_id")
        if not candidate_id:
            continue
        for proposition_id in (_get(candidate, "proposition_ids", ()) or ()):
            memberships.setdefault(proposition_id, []).append(str(candidate_id))
    shared_ids = sorted(candidate_id for candidate_id in memberships.values() if len(candidate_id) > 1)
    shared_branch = ("sahs:shared:" + sha256(json.dumps(shared_ids).encode()).hexdigest()[:12]
                     if shared_ids else None)
    available_sources = {(source_id, version)
                         for source_id, version, *_ in assignment.manifest.source_versions}
    for rule in rules:
        for ref in (_get(rule, "source_refs", ()) or ()):
            source_pair = (_get(ref, "source_id"), _get(ref, "source_version"))
            if available_sources and source_pair not in available_sources:
                raise IntegrationError(f"SAHS cites source/version outside its Lead assignment: {source_pair}")
            if not available_sources:
                catalog = assignment.context.get("source_catalog", ())
                if not any((_get(item, "material_id"), _get(item, "version")) == source_pair
                           for item in catalog):
                    raise IntegrationError(f"SAHS cites source/version not present in Lead assignment: {source_pair}")
    claims = [{
        "claim_id": _get(prop, "proposition_id"),
        "text": _get(prop, "text"),
        "kind": _get(prop, "kind", "hypothesis"),
        "branch_id": _branch_for_proposition(result, prop, memberships, shared_branch),
        "parent_claim_ids": tuple(_get(prop, "parent_claim_ids", ()) or assignment.target_ids),
        "dependency_ids": tuple(_get(prop, "dependency_ids", ()) or ()),
        "provenance": tuple(_get(ref, "source_id") for ref in (_get(prop, "source_refs", ()) or ())),
    } for prop in props]
    links = []
    link_ids_by_rule: dict[str, list[str]] = {}
    for rule in rules:
        refs = tuple(_get(rule, "source_refs", ()) or ())
        basis = _get(rule, "basis", "model_proposed")
        if basis == "source_described" and not refs:
            raise IntegrationError("source-described SAHS rule has no source passage")
        # CFERP currently stores one source passage per causal link. Split a
        # multi-source SAHS rule into provenance-specific links instead of
        # pairing one quote with a list of unrelated source IDs.
        provenance_rows = refs if basis == "source_described" else (None,)
        for idx, ref in enumerate(provenance_rows):
            refs_for_row = (ref,) if ref is not None else refs
            link_id = _get(rule, "rule_id")
            if len(provenance_rows) > 1:
                link_id = f"{link_id}:source:{idx}"
            link_ids_by_rule.setdefault(str(_get(rule, "rule_id")), []).append(link_id)
            links.append({
                "link_id": link_id,
                "source_claim_ids": tuple(_get(rule, "antecedent_ids", ()) or ()),
                "target_claim_id": _get(rule, "consequent_id"),
                "relation": _get(rule, "relation", "may_cause"),
                "modality": _get(rule, "modality", "may"),
                "basis": basis,
                "source_refs": tuple(_get(row_ref, "source_id") for row_ref in refs_for_row),
                "source_relation": _get(rule, "source_relation") or "inference",
                "source_text": _get(ref, "exact_text", "") if ref is not None else "",
                "conditions": tuple(_get(rule, "conditions", ()) or ()),
                "time_constraint": _get(rule, "time_constraint") or "unknown",
            })
    needs = []
    for gap in (_get(result, "information_gaps", ()) or ()):
        need_id = _get(gap, "need_id")
        question = _get(gap, "unknown", "")
        needs.append({"need_id": need_id, "target_ids": _linked_targets(gap, assignment.target_ids),
                      "slots": [{"slot_id": f"{need_id}:slot", "description": question,
                                 "record_type": _get(gap, "information_that_could_resolve_it", "")}],
                      "origin_kind": "specialist_gap"})
    clarifications = []
    for item in (_get(result, "clarification_items", ()) or ()):
        clarification_id = _get(item, "clarification_id")
        question = _get(item, "question", "")
        clarifications.append({"need_id": clarification_id, "target_ids": _linked_targets(item, assignment.target_ids),
                               "slots": [{"slot_id": f"{clarification_id}:slot", "description": question,
                                          "record_type": "term_or_configuration_clarification"}],
                               "origin_kind": "specialist_clarification"})
    payload = {"specialist_status": status, "claims": claims, "causal_links": links, "needs": needs,
               "clarifications": clarifications,
               "candidate_memberships": [{"candidate_id": _get(candidate, "candidate_id"),
                   "proposition_ids": tuple(_get(candidate, "proposition_ids", ()) or ()),
                   # A rule split into per-source links is a member through every link.
                   "rule_ids": tuple(link_id for rule_id in (_get(candidate, "rule_ids", ()) or ())
                                     for link_id in link_ids_by_rule.get(str(rule_id), (rule_id,)))}
                   for candidate in candidates]}
    return RoleResult(result_id or f"sahs:{assignment.assignment_id}", assignment.assignment_id,
                      Role.SPECIALIST, assignment.manifest, payload)


def ew_result_to_cferp(result: Any, assignment: Assignment, *,
                       claim_id_by_slot: dict[str, str | Iterable[str]] | None = None,
                       result_id: str | None = None) -> RoleResult:
    """Normalize EWV3 passages and request drafts for the Lead's commit gate.

    The Lead assignment is authoritative for claim and need identity. If an EW
    assignment covers multiple claims, the Lead must supply slot-to-claim links
    rather than letting the adapter guess.
    """
    if _get(assignment, "role") != Role.EVIDENCE_WORKER:
        raise IntegrationError("EW result requires an Evidence Worker Lead assignment")
    if (_get(result, "assignment_id") != assignment.assignment_id
            or _get(result, "work_item_id") != assignment.assignment_id
            or _get(result, "case_snapshot_id") != assignment.manifest.case_snapshot_id
            or str(_get(result, "board_version")) != str(assignment.manifest.board_version)):
        raise IntegrationError("EWV3 result does not match its Lead assignment snapshot")
    # "no_candidate_in_scope" is a finished search that found nothing relevant:
    # it carries no passages and no requests, and settles the worker pass.
    if _get(result, "status") not in {"ready_for_assessor", "no_candidate_in_scope"}:
        raise IntegrationError(f"EWV3 result is not ready for Lead review: {_get(result, 'status')}")
    # The Lead need's target set applies to its slots unless it supplies a
    # narrower per-slot mapping. Keep that explicit association through the
    # adapter: a retrieved passage is a candidate for each linked claim, while
    # HERA still makes a separate claim–passage assessment for every claim.
    slot_claims: dict[str, tuple[str, ...]] = {}
    context = _get(assignment, "context", {}) or {}
    explicit_map = context.get("claim_ids_by_slot", {}) if isinstance(context, dict) else {}
    explicit_map = explicit_map or {}
    raw_needs = context.get("needs", ()) if isinstance(context, dict) else ()
    if isinstance(context, dict) and context.get("need") is not None:
        raw_needs = (*raw_needs, context["need"])
    for need in raw_needs:
        need_targets = tuple(_get(need, "target_ids", ()) or ())
        for slot in (_get(need, "slots", ()) or ()):
            slot_id = str(_get(slot, "slot_id", ""))
            if slot_id:
                targets = tuple(_get(slot, "target_ids", ()) or need_targets)
                if targets:
                    slot_claims[slot_id] = targets
    for slot_id, targets in explicit_map.items():
        slot_claims[str(slot_id)] = (targets,) if isinstance(targets, str) else tuple(targets)
    for slot_id, targets in (claim_id_by_slot or {}).items():
        slot_claims[str(slot_id)] = (targets,) if isinstance(targets, str) else tuple(targets)
    # Preserve the simple one-claim adapter path for callers that predate
    # carrying Need objects in Assignment.context.
    if not slot_claims and len(assignment.target_ids) == 1:
        slot_claims = {str(_get(slot, "slot_id")): (assignment.target_ids[0],)
                       for slot in (_get(result, "slot_results", ()) or ())}
    links_by_need: dict[str, list[dict[str, Any]]] = {}
    covered_by_need: dict[str, list[str]] = {}
    all_links = []
    def collect_link(need_id: str, slot_id: str, link: Any) -> None:
        claim_ids = slot_claims.get(slot_id, ())
        if not claim_ids or set(claim_ids) - set(assignment.target_ids):
            raise IntegrationError(f"Lead did not assign a claim for EW slot {slot_id}")
        if need_id not in assignment.need_ids:
            raise IntegrationError(f"EW result references an unassigned need {need_id}")
        linked_version = (_get(link, "source_id"), _get(link, "source_version"))
        if not any((source_id, version) == linked_version
                   for source_id, version, _ in assignment.manifest.source_versions):
            raise IntegrationError(f"EWV3 passage source/version is outside the Lead snapshot: {linked_version}")
        for claim_id in claim_ids:
            row = {
                    "claim_id": claim_id,
                    "material_id": _get(link, "source_id"),
                    "material_version": _get(link, "source_version"),
                    "passage_id": _get(link, "candidate_link_id"),
                    "start_offset": _get(link, "start_offset"),
                    "end_offset": _get(link, "end_offset"),
                    "exact_text": _get(link, "exact_text", ""),
                    "need_ids": (need_id,),
                    "slot_id": slot_id,
                    "title": _get(link, "title", ""),
                    "source_kind": _get(link, "source_kind", "unknown"),
                    "channel": _get(link, "channel", "unknown"),
                    "passage_context": _passage_context(_get(link, "structural_context", {}) or {}),
                }
            all_links.append(row)
            links_by_need.setdefault(need_id, []).append(row)
        covered_by_need.setdefault(need_id, []).append(slot_id)

    for slot_result in (_get(result, "slot_results", ()) or ()):
        need_id = _get(slot_result, "need_id")
        slot_id = _get(slot_result, "slot_id")
        for link in (_get(slot_result, "candidate_links", ()) or ()):
            collect_link(need_id, slot_id, link)
    for link in (_get(result, "preserved_candidate_links", ()) or ()):
        collect_link(_get(link, "need_id"), _get(link, "slot_id"), link)
    packets = []
    for index, (need_id, links) in enumerate(sorted(links_by_need.items())):
        linked_source_ids = {link["material_id"] for link in links}
        pinned_versions = tuple(item for item in assignment.manifest.source_versions
                                if item[0] in linked_source_ids)
        packets.append({"packet_id": f"packet:{assignment.assignment_id}:{index}",
                        "target_ids": tuple(dict.fromkeys(link["claim_id"] for link in links)),
                        "covered_slot_ids": tuple(dict.fromkeys(covered_by_need[need_id])),
                        "source_versions": pinned_versions,
                        "searched_material_index_version": assignment.manifest.material_index_version,
                        "candidate_links": links})
    requests = []
    for draft in (_get(result, "request_drafts", ()) or ()):
        slot_ids = tuple(_get(draft, "slot_ids", ()) or ())
        if not slot_ids:
            raise IntegrationError("EWV3 request draft has no linked slot")
        requests.append({
            "request_id": _get(draft, "request_id"),
            "origin_ids": tuple(assignment.need_ids),
            "target_ids": tuple(assignment.target_ids),
            "slot_ids": slot_ids,
            "question_or_document": _get(draft, "question_or_document", ""),
            "request_type": _get(draft, "request_type", "question"),
            "requested_fields": tuple(_get(draft, "requested_fields", ()) or ()),
            "why_it_may_help": _get(draft, "why_it_may_help", ""),
            "source_scope": tuple(_get(draft, "searched_scope", ()) or ()),
            "entity_scope": tuple(_get(draft, "entity_scope", ()) or ()),
            "time_scope": _get(draft, "time_scope") or None,
            "record_types": (),
        })
    return RoleResult(result_id or f"ewv3:{assignment.assignment_id}", assignment.assignment_id,
                      Role.EVIDENCE_WORKER, assignment.manifest,
                      {"packets": packets, "requests": requests})


def _linked_targets(item: Any, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    values = _get(item, "linked_proposition_ids", ()) or ()
    if values:
        return tuple(dict.fromkeys(values))
    # A gap without an explicit link stays attached to the active Lead target;
    # the commit gate still validates these IDs against its case board.
    return tuple(default)


def _branch_for_proposition(result: Any, proposition: Any, memberships: dict[str, list[str]],
                            shared_branch: str | None) -> str:
    proposition_id = _get(proposition, "proposition_id")
    candidate_ids = memberships.get(proposition_id, ())
    if len(candidate_ids) > 1:
        return str(shared_branch)
    if candidate_ids:
        return f"sahs:candidate:{candidate_ids[0]}"
    return f"sahs:unassigned:{_get(result, 'assignment_id')}"


def hera_result_to_cferp(result: Any, task: Any, assignment: Assignment,
                         *, result_id: str | None = None) -> RoleResult:
    """Translate a completed HERA result without collapsing source-level findings.

    Evidence findings become one CFERP annotation per cited claim/source passage.
    General/unclear/non-addressing findings map to ``neutral``. Mixed findings
    remain separate rows. Request and clarification outcomes retain their own
    Lead-facing task kinds and statuses.
    """
    if _get(result, "status") != "completed":
        raise IntegrationError(f"cannot commit non-completed HERA result: {_get(result, 'status')}")
    expected_work_item = assignment.context.get("source_work_item_id", assignment.assignment_id)
    if (_get(result, "task_id") != _get(task, "task_id")
            or _get(result, "work_item_id") != expected_work_item
            or _get(result, "case_snapshot_id") != assignment.manifest.case_snapshot_id
            or _get(result, "case_id") != assignment.manifest.case_id
            or str(_get(result, "board_version")) != str(assignment.manifest.board_version)):
        raise IntegrationError("HERA result does not match its task/Lead assignment snapshot")

    kind = _get(task, "task_kind")
    payload = _get(result, "payload", {}) or {}
    if kind in {"evidence_review", "reassessment_triage"}:
        rows = _evidence_rows(payload, task, assignment)
        normalized = {"task_kind": kind, "assessments": rows}
        if kind == "reassessment_triage":
            prior_ids = tuple(assignment.context.get("prior_assessment_ids", ()))
            if not prior_ids:
                raise IntegrationError("reassessment Lead assignment has no prior assessment IDs")
            normalized["assessments"] = [{**row, "reassesses": prior_ids} for row in rows]
    elif kind == "request_review":
        disposition = payload.get("disposition")
        mapped = {"eligible": "pass", "revise": "revise", "not_eligible": "reject"}.get(disposition)
        if mapped is None:
            raise IntegrationError(f"unsupported HERA request disposition: {disposition!r}")
        normalized = {
            "task_kind": "request_review",
            "request_id": payload.get("request_id") or _get(task, "request", {}).get("request_id"),
            "disposition": mapped,
            "feedback": payload.get("revision_feedback", "") or payload.get("rationale", ""),
            "revised_request": payload.get("revised_request", ""),
            "assessor_context": payload,
        }
        if not normalized["request_id"]:
            raise IntegrationError("HERA request result has no request ID")
    elif kind == "clarification_review":
        status = payload.get("status")
        mapped = {"answered": "accepted", "partial": "partially_accepted",
                  "unanswered": "ambiguous", "ambiguous": "ambiguous",
                  "conflicting": "ambiguous"}.get(status)
        if mapped is None:
            raise IntegrationError(f"unsupported HERA clarification status: {status!r}")
        normalized = {
            "task_kind": "clarification_review",
            "clarification_id": payload.get("clarification_id") or _get(task, "clarification", {}).get("question_id"),
            "decision": mapped,
            "assessor_context": payload,
        }
        if not normalized["clarification_id"]:
            raise IntegrationError("HERA clarification result has no clarification ID")
    else:
        raise IntegrationError(f"unsupported HERA task kind: {kind!r}")

    return RoleResult(result_id or f"hera:{_get(result, 'task_id')}", assignment.assignment_id,
                      Role.ASSESSOR, assignment.manifest, normalized)


def _evidence_rows(payload: dict[str, Any], task: Any, assignment: Assignment) -> list[dict[str, Any]]:
    source_statements = {row.get("statement_id"): row for row in payload.get("source_statements", ())
                         if isinstance(row, dict) and row.get("statement_id")}
    parts = {part.get("part_id"): part for part in (_get(task, "hypothesis", {}) or {}).get("parts", ())
             if isinstance(part, dict) and part.get("part_id")}
    if not payload.get("parts"):
        # HERA may complete an evidence task with no extractable statement.
        # Return neutral for the exact assigned passage so CFERP can close the
        # review without treating retrieval failure as contradiction.
        rows = []
        for part in parts.values():
            claim_ids = tuple(dict.fromkeys(part.get("board_ids", ())))
            if not claim_ids or set(claim_ids) - set(assignment.target_ids):
                raise IntegrationError("HERA no-extraction result exceeds assigned claim scope")
            rows.extend(_neutral_assigned_row(task, assignment, claim_id, len(rows))
                        for claim_id in claim_ids)
        return rows
    allowed_claims = set(assignment.target_ids)
    rows: list[dict[str, Any]] = []
    index = 0
    for assessed_part in payload.get("parts", ()):
        if not isinstance(assessed_part, dict):
            continue
        source_part = parts.get(assessed_part.get("part_id"))
        if source_part is None:
            raise IntegrationError("HERA returned an unknown hypothesis part")
        claim_ids = tuple(dict.fromkeys(source_part.get("board_ids", ())))
        if not claim_ids or set(claim_ids) - allowed_claims:
            raise IntegrationError("Lead assignment does not authorize the HERA claim target")
        findings = assessed_part.get("findings", ()) or ()
        if not findings:
            for claim_id in claim_ids:
                rows.append(_neutral_assigned_row(task, assignment, claim_id, index,
                    str(assessed_part.get("reason", "No relevant source statement was extracted."))))
                index += 1
            continue
        for finding in findings:
            relation = finding.get("relation")
            effect = {"supports": "supports", "weakens": "weakens", "contradicts": "contradicts",
                      "does_not_address": "neutral", "insufficient_or_unclear": "neutral"}.get(relation)
            if effect is None:
                raise IntegrationError(f"unsupported HERA evidence relation: {relation!r}")
            statement_ids = finding.get("statement_ids", ())
            if not statement_ids:
                if effect == "neutral":
                    for claim_id in claim_ids:
                        rows.append(_neutral_assigned_row(task, assignment, claim_id, index,
                                                           str(finding.get("rationale", "No cited finding."))))
                        index += 1
                continue
            for statement_id in statement_ids:
                statement = source_statements.get(statement_id)
                if statement is None:
                    raise IntegrationError("HERA finding references an unknown source statement")
                assigned_link = assignment.context.get("candidate_link", {})
                if assigned_link and statement.get("material_id") != assigned_link.get("passage_id"):
                    raise IntegrationError("HERA assessed a passage outside this CFERP Assessor assignment")
                material_id = statement.get("source_id")
                if not isinstance(material_id, str) or not material_id:
                    raise IntegrationError("HERA source statement is missing source_id")
                quote = str(statement.get("quote", ""))
                if assigned_link:
                    # The review is of the assigned passage; HERA may quote only
                    # part of it (one cell of a table row, say). The row names the
                    # passage the Lead assigned and carries the quote beside it.
                    if quote not in str(assigned_link.get("exact_text", "")):
                        raise IntegrationError("HERA quote is not inside the assigned passage")
                    span = {"exact_text": assigned_link.get("exact_text", ""),
                            "start_offset": assigned_link.get("start_offset"),
                            "end_offset": assigned_link.get("end_offset")}
                else:
                    span = {"exact_text": quote, "start_offset": statement.get("start_offset"),
                            "end_offset": statement.get("end_offset")}
                for claim_id in claim_ids:
                    rows.append({
                        "assessment_id": f"hera:{_get(task, 'task_id')}:{index}",
                        "claim_id": claim_id,
                        "material_id": material_id,
                        "material_version": statement.get("source_version"),
                        # CFERP binds review to the EWV3 candidate-link ID;
                        # HERA's material_id is that link ID, while source_id
                        # is the underlying CFERP document/material ID.
                        "passage_id": statement.get("material_id"),
                        "hera_statement_id": statement_id,
                        **span,
                        "quote": quote,
                        "effect": effect,
                        "rationale": str(finding.get("rationale", "")),
                    })
                    index += 1
    return rows


def _neutral_assigned_row(task: Any, assignment: Assignment, claim_id: str, index: int,
                          rationale: str = "No relevant source statement was extracted.") -> dict[str, Any]:
    link = assignment.context.get("candidate_link", {})
    passage_id = link.get("passage_id")
    material_id = link.get("material_id")
    version = link.get("material_version")
    exact_text = link.get("exact_text", "")
    start = link.get("start_offset")
    end = link.get("end_offset")
    if not passage_id or not material_id:
        materials = _get(task, "materials", ()) or ()
        if not materials:
            raise IntegrationError("cannot normalize an uncited HERA finding without an assigned passage")
        material = materials[0]
        passage_id = _get(material, "material_id")
        material_id = _get(material, "source_id")
        version = _get(material, "source_version")
        exact_text = _get(material, "text", "")
        start = _get(material, "offset_base", 0)
        end = start + len(exact_text)
    return {
        "assessment_id": f"hera:{_get(task, 'task_id')}:{index}",
        "claim_id": claim_id, "material_id": material_id, "material_version": version,
        "passage_id": passage_id, "start_offset": start, "end_offset": end,
        "exact_text": exact_text, "effect": "neutral", "rationale": rationale,
    }


def _get(obj: Any, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)
