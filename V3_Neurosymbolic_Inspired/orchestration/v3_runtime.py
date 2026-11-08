"""Complete V3 Intake-to-Lead runtime boundary.

PIRIS owns submission registration and indexing. This runtime translates its
arrival packet into CFERP material events, starts the Lead workflow, and then
drains ready Specialist, Evidence Worker, and Assessor jobs through the V3
bridge. It deliberately leaves outward dispatch and human responses to the
host/operator.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Any, Iterable

from cferp import CFERPWorkflow
from cferp.workflow import MaterialRecord as LeadMaterialRecord
from piris import (
    AskIntakeInterpreter, IncomingItem, InMemoryMaterialIndexer,
    IntakeAssignment, IntakeEngine, ParserRouter, RequestReference,
)

from .v3_bridge import V3PackageBridge


_LEAD_MATCH_SYSTEM = """You are a bounded metadata matcher for the investigation Lead.
Return JSON only: {\"match_ids\":[\"...\"]}. Select only IDs from the supplied
candidate list that this new material may relate to. This is a routing hint,
not an evidence judgment. Do not create IDs, merge requests, decide what a
document proves, or change the board."""

_LEAD_ASSIGNMENT_SYSTEM = """You may clarify an ambiguous Lead task without widening it.
Return JSON with only these fields: purpose, target_ids, need_ids,
context_additions. Keep all IDs within the supplied assignment. context_additions
may contain only routing_note. Do not create tasks, approve outward requests,
assess evidence, or change the board."""


class ModelLeadSemanticAssistant:
    """Adapter for CFERP's optional, bounded model-backed semantic helper."""

    def __init__(self, model: Any) -> None:
        self.model = model

    def suggest_matches(self, kind: str, candidate: dict[str, Any],
                        existing: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
        result = self.model.ask("cferp_semantic_match", _LEAD_MATCH_SYSTEM, {
            "kind": kind, "candidate": candidate, "candidates": list(existing),
        })
        ids = result.get("match_ids") if isinstance(result, dict) else None
        if not isinstance(ids, list) or not all(isinstance(value, str) for value in ids):
            raise ValueError("Lead semantic matcher must return a match_ids string list")
        return tuple(ids)

    def clarify_assignment(self, assignment: Any) -> dict[str, Any]:
        result = self.model.ask("cferp_assignment_clarification", _LEAD_ASSIGNMENT_SYSTEM, {
            "assignment_id": assignment.assignment_id,
            "role": assignment.role.value,
            "purpose": assignment.purpose,
            "target_ids": list(assignment.target_ids),
            "need_ids": list(assignment.need_ids),
            "context": assignment.context,
        })
        if not isinstance(result, dict):
            raise ValueError("Lead assignment clarification must be a JSON object")
        return result


# Backward-compatible name retained for integrations built against v0.2.
OpenRouterLeadSemanticAssistant = ModelLeadSemanticAssistant


def _jsonable(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray)):
        return {"byte_length": len(value), "sha256": sha256(value).hexdigest()}
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "items") and callable(value.items):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


class V3CaseRuntime:
    """Intake, Lead, Specialist, Evidence Worker, and Assessor runtime.

    Use ``from_openrouter`` for OpenRouter or ``from_ollama`` for an installed
    local Ollama model. The same model client serves every optional V3 model
    port so a run is attributable to one provider/model configuration.
    """

    def __init__(self, workflow: CFERPWorkflow, intake: IntakeEngine,
                 bridge: V3PackageBridge, *, model_client: Any | None = None) -> None:
        if bridge.workflow is not workflow:
            raise ValueError("V3 bridge and runtime must share one CFERP workflow")
        self.workflow = workflow
        self.intake = intake
        self.bridge = bridge
        self.model_client = model_client
        self.started = False
        self.intake_results: list[Any] = []
        self.intake_item_material_ids: dict[str, str] = {}

    @classmethod
    def from_openrouter(cls, case_id: str, *, model: str = "nvidia/nemotron-3-ultra-550b-a55b:free",
                        base_url: str = "https://openrouter.ai/api/v1",
                        timeout: float = 120, retries: int = 1,
                        response_format: str = "off",
                        enable_intake_interpreter: bool = True,
                        enable_lead_semantics: bool = True,
                        retriever: Any | None = None) -> "V3CaseRuntime":
        """Build the standalone V3 runtime around the archive's OpenRouter client."""
        from shared.llm.client import ChatCompletionsModel

        model_client = ChatCompletionsModel(
            provider="openrouter", model=model, base_url=base_url,
            timeout=timeout, retries=retries, response_format=response_format,
        )
        assistant = ModelLeadSemanticAssistant(model_client) if enable_lead_semantics else None
        workflow = CFERPWorkflow(case_id, semantic_assistant=assistant)
        intake = IntakeEngine(
            parser=ParserRouter(), indexer=InMemoryMaterialIndexer(),
            interpreter=AskIntakeInterpreter(model_client.ask) if enable_intake_interpreter else None,
        )
        bridge = V3PackageBridge.from_models(
            workflow, specialist_model=model_client,
            evidence_worker_model=model_client, assessor_model=model_client,
            retriever=retriever,
        )
        return cls(workflow, intake, bridge, model_client=model_client)

    @classmethod
    def from_ollama(cls, case_id: str, *, model: str,
                    base_url: str = "http://localhost:11434",
                    timeout: float = 300, retries: int = 1,
                    response_format: str = "json_object",
                    temperature: float | None = 0.0,
                    keep_alive: str | None = None,
                    structured_output: bool = True,
                    schema_retries: int = 2,
                    num_ctx: int | None = None,
                    answer_reserve_tokens: int = 0,
                    think: str | bool | None = None,
                    assessor_output_retries: int = 1,
                    assessor_reuse_judgments: bool = True,
                    enable_intake_interpreter: bool = True,
                    enable_lead_semantics: bool = True,
                    retriever: Any | None = None) -> "V3CaseRuntime":
        """Build V3 around the native local Ollama ``/api/chat`` adapter.

        With ``structured_output`` the SAHS proposal and HERA extract/compare
        schemas are passed to Ollama as the request ``format`` and replies are schema-checked with at most
        ``schema_retries`` retries; Python proposal validation is unchanged.
        ``assessor_output_retries`` lets HERA re-ask once, showing the model its
        validation error, when a reply fails its Python checks (0 turns it off).
        With ``num_ctx`` set, ``answer_reserve_tokens`` of the window are kept free
        for the Specialist's reasoning and answer: its prompt is trimmed to fit
        the rest (0 sends it whole). ``think`` sets the model's reasoning
        effort for every role (``None``: the model's default).
        ``assessor_reuse_judgments`` makes HERA reuse its judgment when the same
        claim and passage are assessed again, for example for another need.
        """
        from shared.llm.factory import create_model_client
        from hera1.config import AssessorConfig
        from hera1.schemas import HERA_TASK_SCHEMAS
        from ewv3.prompts import EWV3_TASK_SCHEMAS
        from sahs.config import SpecialistConfig
        from sahs.prompt_builder import PROPOSAL_FORMAT_SCHEMA

        model_client = create_model_client(
            provider="ollama_native", model=model, base_url=base_url,
            timeout=timeout, retries=retries, response_format=response_format,
            temperature=temperature, keep_alive=keep_alive,
            task_schemas=({"sahs_proposal": PROPOSAL_FORMAT_SCHEMA, **HERA_TASK_SCHEMAS, **EWV3_TASK_SCHEMAS}
                          if structured_output else None),
            schema_retries=schema_retries, num_ctx=num_ctx, think=think,
        )
        assistant = ModelLeadSemanticAssistant(model_client) if enable_lead_semantics else None
        workflow = CFERPWorkflow(case_id, semantic_assistant=assistant)
        intake = IntakeEngine(
            parser=ParserRouter(), indexer=InMemoryMaterialIndexer(),
            interpreter=AskIntakeInterpreter(model_client.ask) if enable_intake_interpreter else None,
        )
        bridge = V3PackageBridge.from_models(
            workflow, specialist_model=model_client,
            evidence_worker_model=model_client, assessor_model=model_client,
            retriever=retriever,
            specialist_config=SpecialistConfig(
                max_prompt_tokens=num_ctx - answer_reserve_tokens if num_ctx and answer_reserve_tokens else None),
            assessor_config=AssessorConfig(max_output_retries=assessor_output_retries,
                                           reuse_identical_judgments=assessor_reuse_judgments),
        )
        return cls(workflow, intake, bridge, model_client=model_client)

    def initialize_case(self, *, case_packet: dict[str, Any],
                        specialist_profiles: Iterable[dict[str, Any]],
                        initial_items: Iterable[IncomingItem],
                        submission_id: str = "initial-submission",
                        received_at: str | None = None,
                        sender_id: str = "case-intake") -> tuple[Any, ...]:
        """Run PIRIS on the opening packet, register materials, then activate CFERP."""
        if self.started:
            raise RuntimeError("case runtime has already been initialized")
        items = tuple(initial_items)
        if not items:
            raise ValueError("initial case intake requires at least one material item")
        intake_result = self._run_intake(
            submission_id=submission_id, items=items, received_at=received_at,
            sender_id=sender_id,
        )
        item_to_material = self._register_intake_result(intake_result)
        self.intake_item_material_ids.update(item_to_material)

        packet = dict(case_packet)
        claims = []
        for source_claim in packet.get("reported_claims", ()):
            claim = dict(source_claim)
            item_ids = tuple(claim.pop("source_item_ids", ()))
            source_ids = tuple(item_to_material[item_id] for item_id in item_ids
                               if item_id in item_to_material)
            claim["provenance"] = tuple(dict.fromkeys((
                *claim.get("provenance", ()), *source_ids,
            )))
            claims.append(claim)
        packet["reported_claims"] = claims
        assignments = self.workflow.initialize_case(
            event_id=f"case-initialized:{submission_id}",
            case_packet=packet,
            specialist_profiles=tuple(specialist_profiles),
        )
        self.started = True
        return assignments

    def submit_material(self, *, submission_id: str, items: Iterable[IncomingItem],
                        request_id: str | None = None,
                        answered_slot_ids: Iterable[str] = (),
                        received_at: str | None = None,
                        sender_id: str = "external-intake") -> tuple[Any, ...]:
        """Intake a later document/note and signal the Lead with the new material.

        ``request_id`` associates a human response with its Lead request. The
        role pipeline still searches and assesses the content before resolving
        any need or returning a clarification to its Specialist.
        """
        if not self.started:
            raise RuntimeError("initialize_case must run before later submissions")
        intake_result = self._run_intake(
            submission_id=submission_id, items=tuple(items), received_at=received_at,
            sender_id=sender_id,
        )
        item_to_material = self._register_intake_result(
            intake_result, request_id=request_id,
            answered_slot_ids=tuple(answered_slot_ids),
        )
        self.intake_item_material_ids.update(item_to_material)
        return tuple(item_to_material.items())

    def _run_intake(self, *, submission_id: str, items: tuple[IncomingItem, ...],
                    received_at: str | None, sender_id: str):
        received_at = received_at or datetime.now(timezone.utc).isoformat()
        requests = tuple(RequestReference(
            request_id=request.request_id,
            description=request.wording,
            status=getattr(request.state, "value", str(request.state)),
        ) for request in self.workflow.lead.requests.values())
        result = self.intake.run(IntakeAssignment(
            schema_version="1", case_id=self.workflow.case_id,
            case_snapshot_id=self.workflow.lead.manifest().case_snapshot_id,
            submission_id=submission_id, received_at=received_at,
            sender_id=sender_id, items=items, request_catalog=requests,
        ))
        self.intake_results.append(result)
        if getattr(result.event.state, "value", result.event.state) == "failed":
            raise RuntimeError(f"PIRIS rejected submission {submission_id}: {result.diagnostics}")
        return result

    def _register_intake_result(self, result: Any, *, request_id: str | None = None,
                                answered_slot_ids: tuple[str, ...] = ()) -> dict[str, str]:
        records_by_item = {item.item_id: item for item in result.event.item_records}
        item_to_material = {item.item_id: item.material_id for item in result.event.item_records}
        input_items_by_id = {}
        for item in result.event.item_records:
            input_items_by_id.setdefault(item.material_id, []).append(item)
        request_by_material: dict[str, set[str]] = {}
        for material_id, item_rows in input_items_by_id.items():
            linked = request_by_material.setdefault(material_id, set())
            if request_id:
                linked.add(request_id)
            for item in item_rows:
                for link in item.links:
                    if link.request_id in self.workflow.lead.requests:
                        linked.add(link.request_id)

        for material in result.materials:
            item_rows = input_items_by_id.get(material.material_id, ())
            related_needs: list[str] = []
            related_claims: list[str] = []
            for item in item_rows:
                for link in item.links:
                    request = self.workflow.lead.requests.get(link.request_id)
                    if request is not None:
                        related_needs.extend(nid for nid in request.origin_ids
                                             if nid in self.workflow.lead.needs)
                        related_claims.extend(cid for cid in request.target_ids
                                              if cid in self.workflow.claims)
            cferp_material = self._to_lead_material(
                material, related_need_ids=tuple(dict.fromkeys(related_needs)),
                related_claim_ids=tuple(dict.fromkeys(related_claims)),
            )
            links = sorted(request_by_material.get(material.material_id, ()))
            if links:
                for linked_request_id in links:
                    self.workflow.register_external_response(
                        event_id=(f"intake-response:{result.submission_id}:"
                                  f"{material.material_id}:{linked_request_id}"),
                        request_id=linked_request_id, material=cferp_material,
                        answered_slot_ids=answered_slot_ids,
                    )
            else:
                self.workflow.register_material(
                    event_id=(f"intake-material:{result.submission_id}:"
                              f"{material.material_id}:{material.version_id}"),
                    material=cferp_material,
                )
        return item_to_material

    @staticmethod
    def _to_lead_material(material: Any, *, related_need_ids: tuple[str, ...],
                          related_claim_ids: tuple[str, ...]) -> LeadMaterialRecord:
        extraction = material.extraction
        text_available = extraction.status in {"ready", "partial"} and bool(extraction.text)
        index_available = material.index_status in {"ready", "partial"}
        readiness = "ready" if text_available and index_available else (
            "processing" if material.index_status == "pending" else "unreadable"
        )
        source_map = [{
            "segment_id": segment.segment_id,
            "text": segment.text,
            "location": _jsonable(segment.location),
        } for segment in extraction.segments]
        metadata = {
            "origin": "piris_intake",
            "submission_ids": list(material.submission_ids),
            "media_type": material.media_type,
            "filename": material.filename,
            "content_digest": material.content_digest,
            "revision_of": material.revision_of,
            "parser_name": extraction.parser_name,
            "parser_version": extraction.parser_version,
            "extraction_status": extraction.status,
            "index_status": material.index_status,
            "source_map": source_map,
            "warnings": list(extraction.warnings),
        }
        return LeadMaterialRecord(
            material_id=material.material_id,
            version=material.version_id,
            content_hash=material.content_digest,
            title=material.filename or material.material_id,
            source_kind=material.declared_kind or "case_material",
            readiness=readiness,
            searchable_ref=f"piris:{material.material_id}:{material.version_id}",
            lineage="submitter_provided",
            provenance_complete=bool(related_need_ids or related_claim_ids),
            related_claim_ids=related_claim_ids,
            related_need_ids=related_need_ids,
            metadata=metadata,
            content=extraction.text if text_available else None,
        )

    def run_ready(self, *, max_jobs: int = 100):
        """Process queued V3 roles until the queue drains or reaches the cap."""
        if not self.started:
            raise RuntimeError("initialize_case must run before role work")
        return self.bridge.run_ready(max_jobs=max_jobs)

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-ready case, board, workflow, and provider-call snapshot."""
        workflow = self.workflow
        data = {
            "schema_version": "v3-runtime-snapshot-1",
            "case_id": workflow.case_id,
            "case_state": workflow.case_state,
            "manifest": workflow.lead.manifest(),
            "board": {
                "claims": tuple(workflow.claims.values()),
                "causal_links": tuple(workflow.causal_links.values()),
                "branches": tuple(workflow.branches.values()),
                "candidate_memberships": tuple(
                    row for rows in workflow.candidate_memberships.values() for row in rows
                ),
                "assessments": tuple(workflow.assessments.values()),
                "needs": tuple(workflow.lead.needs.values()),
                "requests": tuple(workflow.lead.requests.values()),
                "materials": tuple(workflow.materials.values()),
            },
            "work": tuple(workflow.lead.work.values()),
            "assignments": tuple(workflow.assignments.values()),
            "lead_events": workflow.lead.events,
            "intake_submissions": tuple(self.intake_results),
            "model_calls": tuple(getattr(self.model_client, "calls", ())),
            "model_raw_responses": tuple(getattr(self.model_client, "raw_responses", ())),
            "job_failures": tuple(getattr(self.bridge, "job_failures", ())),
            "outward_requests_require_operator_dispatch": True,
        }
        return _jsonable(data)


__all__ = ["ModelLeadSemanticAssistant", "OpenRouterLeadSemanticAssistant", "V3CaseRuntime"]
