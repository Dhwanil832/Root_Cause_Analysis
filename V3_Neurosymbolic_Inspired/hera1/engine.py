"""Standalone HERA1 orchestration: validate, review, recheck, return delta."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import re
from typing import Any

from .config import AssessorConfig
from .contracts import AssessmentResult, AssessmentTask
from .ledger import InMemoryAssessmentLedger
from .lifecycle import aggregate_relations, destination
from .ports import AssessmentLedger, AssessorModel, VersionReader
from .prompts import PROMPTS
from .validation import (
    ModelOutputError, StaleInput, ValidationError, check_snapshot,
    validate_comparison, validate_statement_batch, validate_task,
    verify_source_spans,
)


class _CountedModel:
    def __init__(self, model: AssessorModel):
        self.model = model
        self.calls = 0
        self.last_step: str | None = None
        self.last_reply: dict[str, Any] | None = None
        self._rejection: dict[str, Any] | None = None

    def reject_last(self, reason: str) -> None:
        """Show the model its rejected reply the next time that step is asked."""
        self._rejection = {"step": self.last_step, "reason": reason, "reply": self.last_reply}

    def ask(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        self.last_step, self.last_reply = name, None
        if self._rejection is not None and self._rejection["step"] == name:
            payload = {**payload, "previous_response_rejected": {
                "reason": self._rejection["reason"], "previous_reply": self._rejection["reply"],
                "instruction": "Return one corrected JSON object that follows the task instructions exactly.",
            }}
            self._rejection = None
        result = self.model.ask(name, PROMPTS[name], payload)
        if not isinstance(result, dict):
            raise ModelOutputError("model response must be a JSON object")
        self.last_reply = result
        return result


class Hera1Engine:
    """Assess packets and return typed results; never writes to the causal board."""

    def __init__(self, model: AssessorModel, versions: VersionReader,
                 ledger: AssessmentLedger | None = None,
                 config: AssessorConfig | None = None) -> None:
        self.model = model
        self.versions = versions
        self.ledger = ledger or InMemoryAssessmentLedger()
        self.config = config or AssessorConfig()
        self._judgments: dict[str, tuple[str, dict[str, Any]]] = {}

    def run(self, task: AssessmentTask) -> AssessmentResult:
        fingerprint = _fingerprint(task)
        claim, previous = self.ledger.begin(task, fingerprint)
        if claim == "duplicate":
            return previous
        if claim == "conflict":
            return self._result(task, "id_conflict", "lead", diagnostics=("event ID reused with changed content",))
        if claim == "busy":
            return self._result(task, "work_item_busy", "lead", diagnostics=("work item already has an active assessment",))

        model = _CountedModel(self.model)
        try:
            validate_task(task, self.config)
            current = self.versions.read(task.case_id, _source_ids(task))
            check_snapshot(task, current)
            unassessable = task.context.get("unassessable_materials", [])
            requires_text = (task.task_kind in {"evidence_review", "reassessment_triage"}
                             or (task.task_kind == "clarification_review"
                                 and task.answer.get("kind") == "document"))
            if requires_text and not task.materials and unassessable:
                result = self._result(task, "unsupported_material", "lead", payload={
                    "unassessable_materials": unassessable,
                    "reason": "No text representation was available to the text-only assessor.",
                })
            elif task.task_kind == "request_review" and _duplicate_request(task):
                result = self._result(task, "duplicate_request", "lead", payload={
                    "disposition": "duplicate", "request_id": task.request["request_id"],
                })
            else:
                payload, reused_from = self._assess(task, model)
                # A concurrent board/document update invalidates this assessment.
                current = self.versions.read(task.case_id, _source_ids(task))
                check_snapshot(task, current)
                role, receiver = destination(task, payload)
                result = self._result(
                    task, "completed", role, receiver, payload, model_calls=model.calls,
                    diagnostics=(f"judgment reused from task {reused_from}",) if reused_from else ())
        except StaleInput as exc:
            result = self._result(task, "stale", "lead", diagnostics=(str(exc),), model_calls=model.calls)
        except ModelOutputError as exc:
            result = self._result(task, "assessment_failed", "lead",
                                  diagnostics=(str(exc),), model_calls=model.calls)
        except ValidationError as exc:
            result = self._result(task, "invalid_input", "sender", task.sender_id,
                                  diagnostics=(str(exc),), model_calls=model.calls)
        except Exception as exc:
            # Provider/transport failures are explicit. No implicit retry or fallback.
            result = self._result(task, "generation_failed", "lead",
                                  diagnostics=(f"{type(exc).__name__}: {exc}",), model_calls=model.calls)
        self.ledger.finish(task, fingerprint, result)
        return result

    def _assess(self, task: AssessmentTask, model: _CountedModel) -> tuple[dict[str, Any], str | None]:
        """Dispatch the task, or reuse an identical earlier evidence judgment.

        The key covers everything the judgment depends on: the claim text, the
        source passage text and where it sits, and prior assessments. It leaves
        out which need or search slot surfaced the passage, so the same passage
        is not re-judged for the same claim. A reused judgment is retargeted to
        this task's passage and still goes through the same snapshot checks and
        Lead commit gate; no model call is made or counted.
        """
        key = _judgment_key(task) if self.config.reuse_identical_judgments else None
        if key is not None and key in self._judgments:
            prior_task_id, prior = self._judgments[key]
            return _retarget_judgment(prior, task.materials[0]), prior_task_id
        payload = self._dispatch_validated(task, model)
        if key is not None:
            self._judgments[key] = (task.task_id, deepcopy(payload))
        return payload, None

    def _dispatch_validated(self, task: AssessmentTask, model: _CountedModel) -> dict[str, Any]:
        """Run the task; on a rejected reply, re-ask that step with the reason, boundedly.

        A reply that still fails validation is rejected: nothing is repaired.
        Earlier steps of the task are asked again on a retry, and every call is
        counted in ``model_calls``.
        """
        reasons: list[str] = []
        while True:
            try:
                return self._dispatch(task, model)
            except ModelOutputError as exc:
                reasons.append(str(exc))
                if len(reasons) > self.config.max_output_retries:
                    if len(reasons) == 1:
                        raise
                    raise ModelOutputError(
                        f"{reasons[-1]} (rejected on {len(reasons)} attempts; earlier: "
                        + "; ".join(reasons[:-1]) + ")") from exc
                model.reject_last(str(exc))

    def _dispatch(self, task: AssessmentTask, model: _CountedModel) -> dict[str, Any]:
        if task.task_kind in {"evidence_review", "reassessment_triage"}:
            return self._review_evidence(task, model)
        if task.task_kind == "clarification_review":
            return self._review_clarification(task, model)
        return self._review_request(task, model)

    def _review_evidence(self, task: AssessmentTask, model: _CountedModel) -> dict[str, Any]:
        materials = [asdict(material) for material in task.materials]
        extracted = model.ask("extract_statements", {
            "materials": materials, "hypothesis": task.hypothesis,
            "context": task.context, "max_statements": self.config.max_extracted_statements,
        })
        statements = validate_statement_batch(extracted, task, self.config)
        if not statements:
            return {
                "evidence_effect": "insufficient", "parts": [], "source_statements": [],
                "reason": "No relevant source statements were extracted from the supplied packet.",
                "requires_more_search": True,
            }
        compared = model.ask("compare_statements", {
            "hypothesis": task.hypothesis, "statements": statements,
            "task_kind": task.task_kind, "context": task.context,
            "prior_assessment_ids": list(task.prior_assessment_ids),
        })
        parts, scope_flags = validate_comparison(compared, task, statements)
        return {
            "evidence_effect": aggregate_relations(parts), "parts": parts,
            "source_statements": statements, "scope_guard_flags": scope_flags,
            "packet_scope_only": True,
            "unassessable_materials": task.context.get("unassessable_materials", []),
            "assessment_coverage": ("partial" if task.context.get("unassessable_materials") else "complete_for_linked_text"),
            "not_found_means": "not assessed in this packet; not a contradiction",
        }

    def _review_clarification(self, task: AssessmentTask, model: _CountedModel) -> dict[str, Any]:
        if task.answer["kind"] == "no_response":
            return {
                "status": "unanswered", "summary": "No response was received.",
                "answered_slots": [], "open_slots": [task.clarification["text"]],
                "ambiguities": [], "conflicts": [], "source_passages": [],
                "answer_basis": "no_response", "verified_truth": False,
                "clarification_id": task.clarification["question_id"],
                "prior_answers_for_lead": list(task.prior_answers),
                "requires_lead_reconciliation": bool(task.prior_answers),
            }
        result = model.ask("review_clarification", {
            "clarification": task.clarification, "answer": task.answer,
            "materials": [asdict(material) for material in task.materials],
            "prior_answers": list(task.prior_answers),
            "unassessable_materials": task.context.get("unassessable_materials", []),
        })
        required = {"status", "summary", "answered_slots", "open_slots",
                    "ambiguities", "conflicts", "source_passages"}
        extra = set(result) - required
        missing = required - set(result)
        if extra or missing:
            raise ModelOutputError(f"clarification response keys invalid; missing={sorted(missing)}, extra={sorted(extra)}")
        allowed = {"answered", "partial", "unanswered", "ambiguous", "conflicting"}
        if result.get("status") not in allowed:
            raise ModelOutputError("clarification status is invalid")
        if not isinstance(result["summary"], str) or not result["summary"].strip():
            raise ModelOutputError("clarification summary must be nonempty text")
        for key in ("answered_slots", "open_slots", "ambiguities", "conflicts", "source_passages"):
            if not isinstance(result[key], list):
                raise ModelOutputError(f"clarification {key} must be an array")
        for key in ("answered_slots", "open_slots", "ambiguities", "conflicts"):
            if any(not isinstance(item, str) or not item.strip() for item in result[key]):
                raise ModelOutputError(f"clarification {key} entries must be nonempty text")
        if result["status"] == "answered" and (not result["answered_slots"] or result["open_slots"]):
            raise ModelOutputError("answered status requires answered slots and no open slots")
        if result["status"] == "answered" and result["conflicts"]:
            raise ModelOutputError("answered status cannot conceal reported conflicts")
        if result["status"] == "partial" and (not result["answered_slots"] or not result["open_slots"]):
            raise ModelOutputError("partial status requires both answered and open slots")
        if result["status"] == "unanswered" and result["answered_slots"]:
            raise ModelOutputError("unanswered status cannot list answered slots")
        if result["status"] == "unanswered" and not result["open_slots"]:
            raise ModelOutputError("unanswered status must preserve open slots")
        if result["status"] == "ambiguous" and not (result["ambiguities"] or result["open_slots"]):
            raise ModelOutputError("ambiguous status requires an ambiguity or open slot")
        if result["status"] == "conflicting" and not result["conflicts"]:
            raise ModelOutputError("conflicting status requires conflict details")
        normalize_slot = lambda item: " ".join(item.casefold().split())
        if {normalize_slot(x) for x in result["answered_slots"]} & {normalize_slot(x) for x in result["open_slots"]}:
            raise ModelOutputError("a clarification slot cannot be both answered and open")
        if task.answer["kind"] in {"human", "note"}:
            if result["source_passages"]:
                raise ModelOutputError("human/note answers cannot return document source passages")
            result["answer_basis"] = "reported_by_responder"
            result["verified_truth"] = False
        elif task.answer["kind"] == "no_response":
            raise ModelOutputError("no_response should bypass model assessment")
        else:
            result["answer_basis"] = "source_linked"
            result["verified_truth"] = False
            if result["status"] in {"answered", "partial", "conflicting"} and not result["source_passages"]:
                raise ModelOutputError("document answer requires source passages for substantive status")
            for passage in result["source_passages"]:
                if not isinstance(passage, dict):
                    raise ModelOutputError("source passage must be an object")
                allowed_passage = {"material_id", "source_id", "source_version", "representation_id",
                                   "quote", "start_offset", "answered_slot"}
                if set(passage) - allowed_passage:
                    raise ModelOutputError("source passage contains unsupported fields")
                slot = passage.get("answered_slot")
                if not isinstance(slot, str) or normalize_slot(slot) not in {
                        normalize_slot(x) for x in result["answered_slots"]}:
                    raise ModelOutputError("each document citation must name one of the answered slots")
            cited_slots = {normalize_slot(p["answered_slot"]) for p in result["source_passages"]}
            if any(normalize_slot(slot) not in cited_slots for slot in result["answered_slots"]):
                raise ModelOutputError("every answered document slot requires its own linked source passage")
            result["source_passages"] = verify_source_spans(result["source_passages"], task.materials)
            weak_source_links = _clarification_citation_gaps(
                task.clarification["text"], result["answered_slots"], result["source_passages"])
            if weak_source_links:
                if result["status"] == "answered":
                    result["status"] = "partial"
                result["open_slots"] = list(dict.fromkeys([*result["open_slots"], *weak_source_links]))
                result["ambiguities"] = list(dict.fromkeys([*result["ambiguities"],
                    "Some cited passages have no clear lexical connection to the clarification question; Lead review is needed."]))
                result["citation_relevance_flags"] = [
                    {"slot": slot, "reason": "no_clear_lexical_anchor_to_question"}
                    for slot in weak_source_links]
            if task.prior_answers:
                result["prior_answers_for_lead"] = list(task.prior_answers)
                result["requires_lead_reconciliation"] = True
        if task.answer["kind"] in {"human", "note"} and task.prior_answers:
            result["prior_answers_for_lead"] = list(task.prior_answers)
            result["requires_lead_reconciliation"] = True
        unassessable = task.context.get("unassessable_materials", [])
        if unassessable:
            if result["status"] == "answered":
                result["status"] = "partial"
            result["open_slots"] = list(dict.fromkeys([*result["open_slots"],
                "Some linked material has no text representation and was not assessed."]))
            result["ambiguities"] = list(dict.fromkeys([*result["ambiguities"],
                "Visual or otherwise non-text material remains unassessed."]))
            result["unassessable_materials"] = unassessable
        result["clarification_id"] = task.clarification["question_id"]
        return result

    def _review_request(self, task: AssessmentTask, model: _CountedModel) -> dict[str, Any]:
        result = model.ask("review_request", {
            "request": task.request, "context": task.context,
            "request_history": list(task.request_history),
        })
        allowed = {"disposition", "rationale", "existing_evidence_status", "existing_evidence_rationale", "proportionality",
                   "revision_feedback", "revised_request"}
        extra = set(result) - allowed
        missing = allowed - set(result)
        if extra or missing:
            raise ModelOutputError(f"request response keys invalid; missing={sorted(missing)}, extra={sorted(extra)}")
        if result.get("disposition") not in {"eligible", "revise", "not_eligible"}:
            raise ModelOutputError("request disposition is invalid")
        if not isinstance(result.get("rationale"), str) or not result["rationale"].strip():
            raise ModelOutputError("request disposition requires a nonempty rationale")
        if result.get("existing_evidence_status") not in {"resolved", "unresolved", "uncertain"}:
            raise ModelOutputError("request existing_evidence_status is invalid")
        if not isinstance(result.get("existing_evidence_rationale"), str) or not result["existing_evidence_rationale"].strip():
            raise ModelOutputError("request existing_evidence_rationale is required")
        found_links = task.context.get("existing_candidate_links", [])
        if found_links:
            link_ids = [row.get("candidate_link_id") for row in found_links if isinstance(row, dict)]
            if not any(isinstance(link_id, str) and link_id and link_id in result["existing_evidence_rationale"]
                       for link_id in link_ids):
                shown = [link_id for link_id in link_ids if isinstance(link_id, str) and link_id][:8]
                raise ModelOutputError(
                    "existing-evidence rationale must identify at least one retrieved candidate link; "
                    "copy an ID exactly as written, including any prefix, from: " + ", ".join(shown))
        if result.get("proportionality") not in {"proportionate", "disproportionate", "uncertain"}:
            raise ModelOutputError("request proportionality is invalid")
        for field in ("revision_feedback", "revised_request"):
            if not isinstance(result.get(field), str):
                raise ModelOutputError(f"request {field} must be text")
        if result["disposition"] == "revise":
            feedback = result.get("revision_feedback")
            revised = result.get("revised_request")
            if not isinstance(feedback, str) or not feedback.strip() or not isinstance(revised, str) or not revised.strip():
                raise ModelOutputError("revise disposition requires concrete feedback and revised_request")
            if task.revision_attempt >= self.config.max_request_revisions:
                return {"disposition": "not_eligible", "reason": "revision_limit_reached",
                        "rationale": "The request revision limit was reached; Lead review is needed.",
                        "revision_feedback": "", "revised_request": "",
                        "prior_revision_feedback": feedback}
        elif result["revision_feedback"] or result["revised_request"]:
            raise ModelOutputError("non-revise request disposition must leave revision fields empty")
        if (result["disposition"] == "revise"
                and result["existing_evidence_status"] == "resolved"):
            return {**result, "disposition": "not_eligible", "reason": "gap_already_resolved",
                    "rationale": "The supplied search context indicates the gap is already resolved; no revised request is routed."}
        if (result["disposition"] == "eligible"
                and (result["existing_evidence_status"] != "unresolved"
                     or result["proportionality"] != "proportionate")):
            return {**result, "disposition": "not_eligible", "reason": "lead_review_required",
                    "rationale": "Eligibility was withheld because the evidence gap or request proportionality is uncertain or already resolved."}
        if (result["disposition"] in {"eligible", "revise"} and found_links
                and (not _rationale_engages_links(result["existing_evidence_rationale"], found_links)
                     or _rationale_discloses_irrelevance(result["existing_evidence_rationale"]))):
            return {**result, "disposition": "not_eligible", "reason": "retrieved_evidence_needs_lead_review",
                    "rationale": "The request rationale does not explain the content of retrieved candidate material; Lead review is needed."}
        if _sensitive_scope(task.request):
            return {**result, "disposition": "not_eligible", "reason": "sensitive_scope_lead_review",
                    "rationale": "The request includes a sensitive personal-data scope and requires Lead review before routing."}
        return result

    @staticmethod
    def _result(task, status, destination_role, destination_id=None, payload=None,
                diagnostics=(), model_calls=0):
        return AssessmentResult(
            schema_version="1", task_id=task.task_id,
            work_item_id=task.work_item_id, event_id=task.event_id,
            case_id=task.case_id, case_snapshot_id=task.case_snapshot_id,
            board_version=task.board_version, task_kind=task.task_kind,
            status=status, destination_role=destination_role,
            destination_id=destination_id, notify_lead=True,
            payload=payload or {}, diagnostics=tuple(diagnostics),
            model_calls=model_calls, resource_usage={"model_calls": model_calls},
        )


def _judgment_key(task: AssessmentTask) -> str | None:
    """Content key for an evidence review of one passage; None if not reusable."""
    if (task.task_kind != "evidence_review" or len(task.materials) != 1
            or task.context.get("unassessable_materials")):
        return None
    material = task.materials[0]
    return hashlib.sha256(json.dumps({
        "hypothesis": task.hypothesis,
        "source": [material.source_id, material.source_version, material.representation_id,
                   material.text, material.offset_base, material.source_kind],
        "prior_assessment_ids": list(task.prior_assessment_ids),
    }, sort_keys=True, default=str).encode()).hexdigest()


def _retarget_judgment(payload: dict[str, Any], material: Any) -> dict[str, Any]:
    """Point a reused judgment's statements at this task's passage ID and location."""
    reused = deepcopy(payload)
    for statement in reused.get("source_statements", ()):
        statement["material_id"] = material.material_id
        statement["location"] = dict(material.location)
    return reused


def _duplicate_request(task: AssessmentTask) -> bool:
    target = task.request
    normalize = lambda value: " ".join(str(value).casefold().split())
    for prior in task.request_history:
        prior_subtype = prior.get("request_type", prior.get("kind", ""))
        target_subtype = target.get("request_type", target.get("kind", ""))
        if (prior.get("target_id") == target.get("target_id")
                and prior.get("kind") == target.get("kind")
                and prior_subtype == target_subtype
                and normalize(prior.get("text", "")) == normalize(target.get("text", ""))):
            return True
    return False


def _fingerprint(task: AssessmentTask) -> str:
    encoded = json.dumps(asdict(task), sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_ids(task: AssessmentTask) -> tuple[str, ...]:
    ids = {m.source_id for m in task.materials}
    for row in task.context.get("unassessable_materials", []):
        if isinstance(row, dict) and isinstance(row.get("source_id"), str):
            ids.add(row["source_id"])
    return tuple(sorted(ids))


def _sensitive_scope(request: dict[str, Any]) -> bool:
    text = " ".join([str(request.get("text", "")),
                     " ".join(str(x) for x in request.get("requested_fields", []))]).casefold()
    cues = ("home address", "residential address", "medical record", "medical history",
            "health chart", "health record", "diagnosis", "date of birth", "dob",
            "social security", "bank account", "password", "personal email",
            "operator emails", "employee emails", "private messages", "chat logs",
            "correspondence", "personal correspondence", "phone number", "phone numbers",
            "mobile number", "mobile numbers", "telephone number", "personnel file",
            "personnel records", "home location", "family details", "family information")
    if any(cue in text for cue in cues):
        return True
    person = r"(?:operator|employee|worker|person|individual|staff|crew)"
    personal_data = r"(?:address|email|correspondence|messages?|date\s+of\s+birth|dob|medical|health|diagnosis|contact\s+details|phone|telephone|mobile|personnel\s+files?|home\s+location|family\s+details?)"
    return bool(re.search(rf"\b{person}\b.{{0,40}}\b{personal_data}\b|\b{personal_data}\b.{{0,40}}\b{person}\b", text))


def _rationale_engages_links(rationale: str, links: list[dict[str, Any]]) -> bool:
    """Require a traceable content hook, not just a candidate-link ID mention."""
    stop = {"the", "and", "for", "with", "from", "that", "this", "was", "were", "are",
            "has", "have", "had", "not", "does", "did", "but", "still", "doesnt", "doesn't",
            "gap", "requested", "request", "fact", "link", "considered", "candidate"}
    rationale_terms = {t for t in re.findall(r"[a-z0-9]+(?::[a-z0-9]+)?", rationale.casefold())
                       if len(t) >= 3 and t not in stop}
    for link in links:
        if not isinstance(link, dict):
            continue
        text_terms = {t for t in re.findall(r"[a-z0-9]+(?::[a-z0-9]+)?", str(link.get("exact_text", "")).casefold())
                      if len(t) >= 3 and t not in stop}
        required = min(2, len(text_terms))
        if required and len(text_terms & rationale_terms) >= required:
            return True
    return False


def _rationale_discloses_irrelevance(rationale: str) -> bool:
    return bool(re.search(r"\b(?:unrelated|irrelevant|not\s+relevant|does\s+not\s+address)\b",
                          rationale.casefold()))


def _clarification_citation_gaps(question: str, answered_slots: list[str], passages: list[dict[str, Any]]) -> list[str]:
    """Flag answered slots whose cited text has no obvious topical word overlap.

    This is only a conservative lexical tripwire. It does not determine semantic
    relevance; flagged answers are downgraded for Lead review rather than rejected.
    """
    stop = {"what", "does", "mean", "refer", "refers", "which", "when", "where", "who",
            "how", "was", "were", "is", "are", "the", "a", "an", "to", "of", "in", "on",
            "for", "and", "or", "it", "this", "that", "with", "about", "identify", "describe"}
    q_terms = {x for x in re.findall(r"\b[a-z0-9-]+\b", question.casefold()) if len(x) >= 3 and x not in stop}
    gaps = []
    for slot in answered_slots:
        matching = [p for p in passages if " ".join(str(p.get("answered_slot", "")).casefold().split())
                    == " ".join(slot.casefold().split())]
        passage_terms = {x for p in matching for x in re.findall(r"\b[a-z0-9-]+\b", str(p.get("quote", "")).casefold())
                         if len(x) >= 3 and x not in stop}
        slot_terms = {x for x in re.findall(r"\b[a-z0-9-]+\b", slot.casefold()) if len(x) >= 3 and x not in stop}
        if not passage_terms.intersection(q_terms | slot_terms):
            gaps.append(slot)
    return gaps
