"""Python-side contract checks and source-span verification for HERA1."""
from __future__ import annotations

from typing import Any
import re

from .config import AssessorConfig
from .contracts import AssessmentTask, EvidenceMaterial, VersionSnapshot


class ValidationError(ValueError):
    pass


class StaleInput(ValidationError):
    pass


class ModelOutputError(ValidationError):
    pass


def _only_keys(value: dict[str, Any], allowed: set[str], label: str) -> None:
    extra = set(value) - allowed
    if extra:
        raise ModelOutputError(f"{label} contains unsupported fields: {sorted(extra)}")


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be nonempty text")
    return value


def validate_task(task: AssessmentTask, config: AssessorConfig) -> None:
    for name in ("schema_version", "task_id", "work_item_id", "event_id", "case_id",
                 "case_snapshot_id", "board_version", "sender_role", "sender_id"):
        _text(getattr(task, name), name)
    if task.schema_version != "1":
        raise ValidationError("unsupported schema_version")
    if task.sender_role not in {"lead", "evidence_worker", "intake"}:
        raise ValidationError("unsupported sender_role")
    if not isinstance(task.context, dict):
        raise ValidationError("context must be an object")
    unassessable = task.context.get("unassessable_materials", [])
    if not isinstance(unassessable, list) or len(unassessable) > config.max_materials:
        raise ValidationError("unassessable_materials must be a bounded array")
    for item in unassessable:
        if not isinstance(item, dict):
            raise ValidationError("unassessable material entries must be objects")
        for name in ("source_id", "source_version", "representation_id"):
            _text(item.get(name), f"unassessable_material.{name}")
    if task.task_kind in {"evidence_review", "reassessment_triage"}:
        if not isinstance(task.hypothesis, dict):
            raise ValidationError(f"{task.task_kind} requires hypothesis")
        parts = task.hypothesis.get("parts")
        if not isinstance(parts, list) or not parts or len(parts) > config.max_hypothesis_parts:
            raise ValidationError("hypothesis.parts must be a nonempty bounded array")
        ids = []
        for part in parts:
            if not isinstance(part, dict):
                raise ValidationError("hypothesis parts must be objects")
            ids.append(_text(part.get("part_id"), "part.part_id"))
            _text(part.get("text"), "part.text")
            if part.get("claim_type") not in {"incident_fact", "incident_causal_link", "general_mechanism", "other"}:
                raise ValidationError("part.claim_type is missing or unsupported")
        if len(ids) != len(set(ids)):
            raise ValidationError("hypothesis part IDs must be unique")
        _validate_materials(task.materials, config)
        if not task.materials and not task.context.get("unassessable_materials"):
            raise ValidationError(f"{task.task_kind} requires at least one linked material")
        if task.task_kind == "reassessment_triage":
            prior_ids = set(task.prior_assessment_ids)
            prior_rows = task.context.get("prior_assessments", [])
            if not prior_ids or not isinstance(prior_rows, list):
                raise ValidationError("reassessment_triage requires prior assessment records")
            if {row.get("assessment_id") for row in prior_rows if isinstance(row, dict)} != prior_ids:
                raise ValidationError("reassessment prior records do not match assigned IDs")
    elif task.task_kind == "clarification_review":
        if not isinstance(task.clarification, dict) or not isinstance(task.answer, dict):
            raise ValidationError("clarification_review requires clarification and answer")
        _text(task.clarification.get("question_id"), "clarification.question_id")
        _text(task.clarification.get("text"), "clarification.text")
        if task.answer.get("kind") not in {"document", "human", "note", "no_response"}:
            raise ValidationError("answer.kind must be document, human, note, or no_response")
        if task.answer.get("question_id") != task.clarification.get("question_id"):
            raise ValidationError("answer.question_id is missing or does not match assigned clarification")
        if task.answer.get("kind") == "document":
            _validate_materials(task.materials, config)
            if not task.materials and not task.context.get("unassessable_materials"):
                raise ValidationError("document-derived answer requires linked material")
        elif task.answer.get("kind") == "no_response":
            if task.answer.get("text", "") not in {"", None}:
                raise ValidationError("no_response answer cannot carry answer text")
        else:
            answer_text = _text(task.answer.get("text"), "answer.text")
            if len(answer_text) > config.max_answer_chars:
                raise ValidationError("answer exceeds max_answer_chars")
    elif task.task_kind == "request_review":
        if not isinstance(task.request, dict):
            raise ValidationError("request_review requires request")
        for name in ("request_id", "target_id", "text"):
            _text(task.request.get(name), f"request.{name}")
        if task.request.get("kind") not in {"question", "document_request"}:
            raise ValidationError("request.kind must be question or document_request")
        requested_fields = task.request.get("requested_fields", [])
        if not isinstance(requested_fields, list) or any(not isinstance(value, str) for value in requested_fields):
            raise ValidationError("request.requested_fields must be an array of strings")
        if len(task.request["text"]) > config.max_request_chars:
            raise ValidationError("request exceeds max_request_chars")
        if len(task.request_history) > config.max_request_history:
            raise ValidationError("request history exceeds configured limit")
        if any(not isinstance(row, dict) for row in task.request_history):
            raise ValidationError("request_history entries must be objects")
        if type(task.revision_attempt) is not int or task.revision_attempt < 0:
            raise ValidationError("revision_attempt must be a nonnegative integer")
    else:
        raise ValidationError("unsupported task_kind")
    context_material = {
        "context": task.context,
        "hypothesis": task.hypothesis,
        "clarification": task.clarification,
        "answer": task.answer if task.answer and task.answer.get("kind") != "human" else None,
        "request": task.request,
        "request_history": task.request_history,
        "prior_answers": task.prior_answers,
    }
    if len(str(context_material)) > config.max_context_chars:
        raise ValidationError("context exceeds max_context_chars")
    if len(task.prior_answers) > config.max_related_answers or any(not isinstance(row, dict) for row in task.prior_answers):
        raise ValidationError("prior_answers must be a bounded array of objects")
    if task.task_kind == "clarification_review":
        for row in task.prior_answers:
            if row.get("question_id") != task.clarification.get("question_id"):
                raise ValidationError("prior answer belongs to another clarification")
            _text(row.get("text"), "prior_answer.text")


def _validate_materials(materials: tuple[EvidenceMaterial, ...], config: AssessorConfig) -> None:
    if len(materials) > config.max_materials:
        raise ValidationError("too many linked materials")
    ids = [m.material_id for m in materials]
    if len(ids) != len(set(ids)):
        raise ValidationError("duplicate material representations")
    total = 0
    for material in materials:
        _text(material.material_id, "material.material_id")
        _text(material.source_id, "material.source_id")
        _text(material.source_version, "material.source_version")
        _text(material.representation_id, "material.representation_id")
        if not isinstance(material.text, str) or not material.text:
            raise ValidationError("material.text must be nonempty")
        if type(material.offset_base) is not int or material.offset_base < 0:
            raise ValidationError("material.offset_base must be a nonnegative integer")
        total += len(material.text)
    if total > config.max_total_material_chars:
        raise ValidationError("linked material text exceeds configured total limit")


def check_snapshot(task: AssessmentTask, current: VersionSnapshot) -> None:
    if current.case_snapshot_id != task.case_snapshot_id:
        raise StaleInput("case_snapshot_changed")
    if current.board_version != task.board_version:
        raise StaleInput("board_version_changed")
    expected_versions = {m.source_id: m.source_version for m in task.materials}
    for row in task.context.get("unassessable_materials", []):
        if isinstance(row, dict) and row.get("source_id") and row.get("source_version"):
            expected_versions[row["source_id"]] = row["source_version"]
    for source_id, source_version in expected_versions.items():
        if current.material_versions.get(source_id) != source_version:
            raise StaleInput(f"material_version_changed:{source_id}")


def verify_source_spans(rows: list[dict[str, Any]], materials: tuple[EvidenceMaterial, ...]) -> list[dict[str, Any]]:
    material_map = {m.material_id: m for m in materials}
    output = []
    for row in rows:
        if not isinstance(row, dict):
            raise ModelOutputError("source reference must be an object")
        material = material_map.get(row.get("material_id"))
        if material is None or (row.get("source_id"), row.get("source_version"), row.get("representation_id")) != (
            material.source_id, material.source_version, material.representation_id
        ):
            raise ModelOutputError("model cited material outside the assigned packet")
        quote = row.get("quote")
        start = row.get("start_offset")
        if not isinstance(quote, str) or len(quote.strip()) < 4:
            raise ModelOutputError("source quote is missing or too short")
        if type(start) is not int or start < 0 or material.text[start:start + len(quote)] != quote:
            occurrences = [i for i in range(len(material.text)) if material.text.startswith(quote, i)]
            if len(occurrences) != 1:
                raise ModelOutputError("quote is not uniquely located in the supplied representation")
            start = occurrences[0]
        location = dict(material.location)
        if location.get("start_offset_missing"):
            # Do not make a snippet-local coordinate look like a source-global one.
            output.append({**row, "start_offset": None, "end_offset": None,
                           "local_start_offset": start,
                           "local_end_offset": start + len(quote),
                           "offset_basis": "representation_text",
                           "location": location})
        else:
            output.append({**row, "start_offset": material.offset_base + start,
                           "end_offset": material.offset_base + start + len(quote),
                           "offset_basis": "source_representation",
                           "location": location})
    return output


def validate_statement_batch(raw: dict[str, Any], task: AssessmentTask, config: AssessorConfig) -> list[dict[str, Any]]:
    _only_keys(raw, {"statements"}, "statement batch")
    statements = raw.get("statements")
    if not isinstance(statements, list) or len(statements) > config.max_extracted_statements:
        raise ModelOutputError("statements must be a bounded array")
    if any(not isinstance(row, dict) for row in statements):
        raise ModelOutputError("each statement must be an object")
    allowed_fields = {"statement_id", "material_id", "source_id", "source_version",
                      "representation_id", "quote", "start_offset", "kind", "modality",
                      "scope", "timing"}
    for row in statements:
        _only_keys(row, allowed_fields, "statement")
    statements = verify_source_spans(statements, task.materials)
    ids = [row.get("statement_id") for row in statements]
    if any(not isinstance(sid, str) or not sid for sid in ids) or len(ids) != len(set(ids)):
        raise ModelOutputError("statement IDs must be unique nonempty strings")
    kinds = {"incident_observation", "reported_event", "incident_causal_statement",
             "general_mechanism", "procedure", "hypothetical", "other"}
    modalities = {"asserted", "reported", "measured", "conditional", "possible", "negated", "inferred", "unclear"}
    if any(row.get("kind") not in kinds or row.get("modality") not in modalities for row in statements):
        raise ModelOutputError("statement kind or modality is invalid")
    if any(not isinstance(row.get("scope"), str) or not isinstance(row.get("timing"), str)
           for row in statements):
        raise ModelOutputError("statement scope and timing must be strings")
    # Reject multiple model IDs for the same cited span. Otherwise the model can
    # manufacture a false mixed result by relabeling one passage twice.
    seen_spans = set()
    for row in statements:
        span = (row["material_id"], row.get("start_offset"), row.get("end_offset"), row["quote"])
        # verify_source_spans normalizes end_offset only for output location; derive
        # the actual representation-local start from the verified quote.
        material = next(m for m in task.materials if m.material_id == row["material_id"])
        start = row.get("local_start_offset")
        if start is None:
            start = row["start_offset"] - material.offset_base
        span = (row["material_id"], start, start + len(row["quote"]), row["quote"])
        if span in seen_spans:
            raise ModelOutputError("the same cited source span cannot be extracted as multiple statements")
        seen_spans.add(span)
        if _has_clear_negation(row["quote"]):
            row["modality"] = "negated"
    return statements


def _has_clear_negation(text: str) -> bool:
    # Conservative surface cue only. This catches straightforward polarity
    # reversals while avoiding broad semantic claims about negation scope.
    return bool(re.search(
        r"\b(?:did\s+not|does\s+not|do\s+not|was\s+not|were\s+not|is\s+not|"
        r"are\s+not|has\s+not|have\s+not|had\s+not|never|no\s+evidence\s+of|"
        r"without|no\s+(?:leak|failure|alarm|pressure\s+loss))\b",
        text, flags=re.IGNORECASE))


def _clear_time_mismatch(quote: str, claim: str) -> bool:
    q, c = quote.casefold(), claim.casefold()
    target_incident_time = bool(re.search(
        r"\b(during|at the time of)\s+(?:(?:the|this|that)\s+)?(?:incident|event|accident)\b", c))
    source_other_time = bool(re.search(
        r"\b(?:previous|prior|next|following|last)\s+shift\b|\b(?:before|after)\s+(?:the\s+)?(?:incident|event|accident)\b",
        q))
    return target_incident_time and source_other_time


def validate_comparison(raw: dict[str, Any], task: AssessmentTask, statements: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _only_keys(raw, {"parts"}, "comparison")
    parts = raw.get("parts")
    expected = {p["part_id"] for p in task.hypothesis["parts"]}
    if not isinstance(parts, list) or len(parts) != len(expected):
        raise ModelOutputError("comparison must return each hypothesis part exactly once")
    allowed = {"supports", "weakens", "contradicts", "does_not_address", "insufficient_or_unclear"}
    known_statement_ids = {s["statement_id"] for s in statements}
    for part in parts:
        if not isinstance(part, dict):
            raise ModelOutputError("comparison part must be an object")
        _only_keys(part, {"part_id", "findings"}, "comparison part")
        findings = part.get("findings")
        if part.get("part_id") not in expected or not isinstance(findings, list) or not findings or len(findings) > 16:
            raise ModelOutputError("comparison part requires a bounded nonempty findings array")
        for finding in findings:
            if not isinstance(finding, dict):
                raise ModelOutputError("comparison finding must be an object")
            _only_keys(finding, {"relation", "statement_ids", "rationale", "inference_bridge",
                                 "relevance_status", "scope_alignment", "time_alignment"}, "comparison finding")
            refs = finding.get("statement_ids")
            if (finding.get("relation") not in allowed
                    or not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs)
                    or not set(refs).issubset(known_statement_ids)):
                raise ModelOutputError("comparison finding has invalid relation or statement reference")
            if finding["relation"] in {"supports", "weakens", "contradicts"} and not refs:
                raise ModelOutputError("impactful finding requires at least one linked source statement")
            if (not isinstance(finding.get("rationale"), str) or not finding["rationale"].strip()
                    or not isinstance(finding.get("inference_bridge"), str)):
                raise ModelOutputError("comparison rationale and inference_bridge must be text")
            if finding.get("relevance_status") not in {"direct", "indirect", "unrelated", "uncertain"}:
                raise ModelOutputError("comparison relevance_status is invalid")
            if finding["relation"] in {"supports", "weakens", "contradicts"} and not finding["inference_bridge"].strip():
                raise ModelOutputError("impactful finding requires an explicit claim-to-source inference bridge")
            for alignment in ("scope_alignment", "time_alignment"):
                if finding.get(alignment) not in {"match", "mismatch", "unknown"}:
                    raise ModelOutputError(f"comparison {alignment} must be match, mismatch, or unknown")
    ids = [p["part_id"] for p in parts]
    if len(ids) != len(set(ids)) or set(ids) != expected:
        raise ModelOutputError("comparison part IDs must cover assigned parts exactly")
    by_id = {s["statement_id"]: s for s in statements}
    part_specs = {p["part_id"]: p for p in task.hypothesis["parts"]}
    scope_flags = []
    for result in parts:
        spec = part_specs[result["part_id"]]
        seen_statement_ids = set()
        for finding_index, finding in enumerate(result["findings"]):
            linked = [by_id[sid] for sid in finding["statement_ids"]]
            if seen_statement_ids.intersection(finding["statement_ids"]):
                raise ModelOutputError("one source statement cannot be assigned to multiple findings for the same part")
            seen_statement_ids.update(finding["statement_ids"])
            if finding["relevance_status"] in {"unrelated", "uncertain"} and finding["relation"] in {"supports", "weakens", "contradicts"}:
                finding["model_relation"] = finding["relation"]
                finding["relation"] = ("does_not_address" if finding["relevance_status"] == "unrelated"
                                       else "insufficient_or_unclear")
                scope_flags.append({"part_id": result["part_id"], "finding_index": finding_index,
                                    "rule": "source_relevance_not_established"})
            if any(_clear_time_mismatch(s["quote"], spec["text"]) for s in linked):
                if finding["relation"] in {"supports", "weakens", "contradicts"}:
                    finding["model_relation"] = finding["relation"]
                    finding["relation"] = "does_not_address"
                    finding["time_alignment"] = "mismatch"
                    scope_flags.append({"part_id": result["part_id"], "finding_index": finding_index,
                                        "rule": "lexical_incident_time_mismatch"})
            if spec["claim_type"] in {"incident_fact", "incident_causal_link"}:
                reason = None
                if finding["relation"] in {"supports", "weakens", "contradicts"}:
                    allowed_kinds = ({"incident_observation", "reported_event", "incident_causal_statement"}
                                     if spec["claim_type"] == "incident_fact"
                                     else {"incident_causal_statement"})
                    if linked and any(s["kind"] not in allowed_kinds for s in linked):
                        reason = "source_type_does_not_assess_incident_claim"
                        finding["model_relation"] = finding["relation"]
                        finding["relation"] = "does_not_address"
                    elif finding["scope_alignment"] == "mismatch" or finding["time_alignment"] == "mismatch":
                        reason = "incident_scope_or_time_mismatch"
                        finding["model_relation"] = finding["relation"]
                        finding["relation"] = "does_not_address"
                    elif finding["scope_alignment"] != "match" or finding["time_alignment"] != "match":
                        reason = "incident_scope_or_time_unresolved"
                        finding["model_relation"] = finding["relation"]
                        finding["relation"] = "insufficient_or_unclear"
                    elif linked and any(s["modality"] not in {"asserted", "reported", "measured", "negated"}
                                        for s in linked):
                        reason = "source_modality_is_not_incident_observation"
                        finding["model_relation"] = finding["relation"]
                        finding["relation"] = "insufficient_or_unclear"
                if finding["relation"] == "supports":
                    allowed_kinds = ({"incident_observation", "reported_event"}
                                     if spec["claim_type"] == "incident_fact"
                                     else {"incident_causal_statement"})
                    if (not linked or any(s["kind"] not in allowed_kinds
                                          or s["modality"] not in {"asserted", "reported", "measured"}
                                          for s in linked)):
                        reason = "source_type_or_polarity_does_not_support_incident_claim"
                        finding["model_relation"] = "supports"
                        finding["relation"] = "insufficient_or_unclear"
                if reason:
                    scope_flags.append({"part_id": result["part_id"], "finding_index": finding_index,
                                        "rule": reason})
        # Retain separate findings but also provide a convenient per-part summary.
        from .lifecycle import aggregate_part_findings
        result["relation"] = aggregate_part_findings(result["findings"])
        result["statement_ids"] = list(dict.fromkeys(
            sid for finding in result["findings"] for sid in finding["statement_ids"]))
    return parts, scope_flags
