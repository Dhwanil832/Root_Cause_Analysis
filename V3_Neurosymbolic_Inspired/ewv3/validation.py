"""Strict assignment, planner-output, and provenance validation."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

from .contracts import EvidenceAssignment, SourceUnit


class EvidenceValidationError(ValueError):
    pass


def validate_assignment(a: EvidenceAssignment, *, max_sources: int, max_text_chars: int) -> None:
    for field in ("schema_version", "assignment_id", "work_item_id", "event_id", "case_id",
                  "case_snapshot_id", "board_version"):
        if not str(getattr(a, field)).strip():
            raise EvidenceValidationError(f"{field} must be non-empty")
    if not a.needs:
        raise EvidenceValidationError("assignment requires at least one need")
    need_ids = [n.need_id for n in a.needs]
    if len(need_ids) != len(set(need_ids)):
        raise EvidenceValidationError("need IDs must be unique")
    slot_ids = [s.slot_id for n in a.needs for s in n.slots]
    if not slot_ids or len(slot_ids) != len(set(slot_ids)):
        raise EvidenceValidationError("answer-slot IDs must be non-empty and globally unique")
    if len(a.sources) > max_sources:
        raise EvidenceValidationError("source count exceeds configured limit")
    source_ids = [s.source_id for s in a.sources]
    if len(source_ids) != len(set(source_ids)):
        raise EvidenceValidationError("source IDs must be unique in one assignment")
    if a.allowed_source_ids and not set(source_ids).issubset(set(a.allowed_source_ids)):
        raise EvidenceValidationError("assignment contains a source outside allowed_source_ids")
    if sum(len(s.text) + sum(len(r.text) for r in s.representations)
           for s in a.sources) > max_text_chars:
        raise EvidenceValidationError("source text exceeds configured input budget")
    for source in a.sources:
        representation_ids = [r.representation_id for r in source.representations]
        if len(representation_ids) != len(set(representation_ids)):
            raise EvidenceValidationError(f"representation IDs must be unique within source {source.source_id}")
        if any(not r.representation_id.strip() or not r.modality.strip() for r in source.representations):
            raise EvidenceValidationError(f"source {source.source_id} has an invalid representation")
    if a.manifest.completeness_status not in {
        "authoritatively_complete", "registered_scope_only", "known_incomplete", "unknown"
    }:
        raise EvidenceValidationError("invalid corpus completeness status")
    if a.manifest.completeness_status == "authoritatively_complete" and not a.manifest.completeness_basis.strip():
        raise EvidenceValidationError("authoritative completeness requires a stated basis")
    for need in a.needs:
        if need.search_objective not in {"candidate_retrieval", "bounded_comparison"}:
            raise EvidenceValidationError(f"unsupported search objective for {need.need_id}")
        if not need.slots or any(not x.description.strip() for x in need.slots):
            raise EvidenceValidationError(f"need {need.need_id} requires described Lead-owned slots")
        slot_by_id = {slot.slot_id: slot for slot in need.slots}
        if need.search_objective == "bounded_comparison" and not need.comparisons:
            raise EvidenceValidationError(
                f"bounded_comparison need {need.need_id} requires Lead-defined comparison groups"
            )
        if need.search_objective == "candidate_retrieval" and need.comparisons:
            raise EvidenceValidationError(
                f"candidate_retrieval need {need.need_id} cannot contain comparison groups"
            )
        comparison_ids = [comparison.comparison_id for comparison in need.comparisons]
        if len(comparison_ids) != len(set(comparison_ids)):
            raise EvidenceValidationError(f"comparison IDs must be unique within need {need.need_id}")
        assigned_to_comparison: set[str] = set()
        for comparison in need.comparisons:
            if not comparison.comparison_id.strip() or not comparison.comparison_dimension.strip():
                raise EvidenceValidationError("comparison ID and dimension must be non-empty")
            if len(comparison.slot_ids) < 2 or len(comparison.slot_ids) != len(set(comparison.slot_ids)):
                raise EvidenceValidationError(
                    f"comparison {comparison.comparison_id} requires at least two distinct slots"
                )
            if not set(comparison.slot_ids).issubset(slot_by_id):
                raise EvidenceValidationError(
                    f"comparison {comparison.comparison_id} references a slot outside need {need.need_id}"
                )
            if assigned_to_comparison.intersection(comparison.slot_ids):
                raise EvidenceValidationError("a slot cannot belong to multiple comparison groups")
            descriptions = [" ".join(slot_by_id[sid].description.casefold().split())
                            for sid in comparison.slot_ids]
            if len(descriptions) != len(set(descriptions)):
                raise EvidenceValidationError("comparison alternatives must have distinct slot descriptions")
            assigned_to_comparison.update(comparison.slot_ids)
    raw_budget = a.budgets.get("max_search_calls", 100)
    if isinstance(raw_budget, bool) or not isinstance(raw_budget, int) or raw_budget < 0:
        raise EvidenceValidationError("max_search_calls must be a nonnegative integer")


def validate_query_plan(raw: Any, assignment: EvidenceAssignment, max_queries_per_slot: int,
                        allowed_slot_ids: set[str] | None = None) -> dict[str, tuple[str, ...]]:
    if not isinstance(raw, dict) or set(raw) != {"queries"} or not isinstance(raw["queries"], list):
        raise EvidenceValidationError("query plan must contain only a queries array")
    assigned_slots = {slot.slot_id for need in assignment.needs for slot in need.slots}
    valid_slots = assigned_slots if allowed_slot_ids is None else assigned_slots & allowed_slot_ids
    output: dict[str, list[str]] = {slot_id: [] for slot_id in valid_slots}
    for row in raw["queries"]:
        if not isinstance(row, dict) or set(row) != {"slot_id", "query"}:
            raise EvidenceValidationError("each query needs exactly slot_id and query")
        slot_id, query = row["slot_id"], row["query"]
        if slot_id not in valid_slots:
            raise EvidenceValidationError(f"query references an unassigned or non-target slot {slot_id!r}")
        if not isinstance(query, str) or not query.strip() or len(query) > 500:
            raise EvidenceValidationError("query must be a non-empty string of at most 500 chars")
        if query not in output[slot_id]:
            output[slot_id].append(query.strip())
        if len(output[slot_id]) > max_queries_per_slot:
            raise EvidenceValidationError(f"query limit exceeded for slot {slot_id}")
    return {k: tuple(v) for k, v in output.items()}


def validate_request_plan(raw: Any, assignment: EvidenceAssignment, allowed_slots: set[str], limit: int):
    if not isinstance(raw, dict) or set(raw) != {"requests"} or not isinstance(raw["requests"], list):
        raise EvidenceValidationError("request plan must contain only a requests array")
    if len(raw["requests"]) > limit:
        raise EvidenceValidationError("request draft limit exceeded")
    valid_slots = {s.slot_id for n in assignment.needs for s in n.slots}
    result = []
    rejected = []
    seen: dict[tuple[str, str], int] = {}
    pending_fingerprints = {
        (p.request_type, " ".join(p.question_or_document.casefold().split()))
        for p in assignment.pending_requests
    }
    for i, row in enumerate(raw["requests"]):
        try:
            fields = {"request_type", "slot_ids", "request", "why_it_may_help", "requested_fields"}
            if not isinstance(row, dict) or set(row) != fields:
                raise EvidenceValidationError("request draft has missing or unknown fields")
            if row["request_type"] not in {"terminology_question", "incident_question", "document_request"}:
                raise EvidenceValidationError("unsupported request_type")
            ids = row["slot_ids"]
            if (not isinstance(ids, list) or not ids
                    or any(not isinstance(x, str) for x in ids)
                    or not set(ids).issubset(valid_slots & allowed_slots)):
                raise EvidenceValidationError("request references an unresolved or unassigned slot")
            if not all(isinstance(row[k], str) and row[k].strip() for k in ("request", "why_it_may_help")):
                raise EvidenceValidationError("request and rationale must be non-empty strings")
            request_fp = " ".join(row["request"].casefold().split())
            key = (row["request_type"], request_fp)
            if key in pending_fingerprints:
                raise EvidenceValidationError("request duplicates an existing pending request")
            requested = row["requested_fields"]
            if not isinstance(requested, list) or not all(isinstance(x, str) for x in requested):
                raise EvidenceValidationError("requested_fields must be a string array")
        except (EvidenceValidationError, KeyError, TypeError) as exc:
            rejected.append(f"request draft {i + 1} rejected: {exc}")
            continue

        normalized = {**row, "slot_ids": list(dict.fromkeys(ids)),
                      "requested_fields": list(dict.fromkeys(x.strip() for x in requested if x.strip()))}
        if key in seen:
            prior = result[seen[key]]
            prior["slot_ids"] = list(dict.fromkeys((*prior["slot_ids"], *normalized["slot_ids"])))
            prior["requested_fields"] = list(dict.fromkeys(
                (*prior["requested_fields"], *normalized["requested_fields"])))
            rationales = list(dict.fromkeys((prior["why_it_may_help"], normalized["why_it_may_help"])))
            prior["why_it_may_help"] = " ".join(rationales)
            rejected.append(f"request draft {i + 1} merged with duplicate request")
        else:
            seen[key] = len(result)
            result.append(normalized)

    for i, row in enumerate(result, 1):
        row["request_id"] = f"req:{assignment.assignment_id}:{i}"
    return tuple(result), tuple(rejected)


def verify_source_span(source: SourceUnit, hit_start: int | None, hit_end: int | None, excerpt: str,
                       *, representation_text: str | None = None) -> str:
    text = source.text if representation_text is None else representation_text
    if hit_start is None or hit_end is None or hit_start < 0 or hit_end <= hit_start or hit_end > len(text):
        raise EvidenceValidationError("retriever returned invalid source offsets")
    actual = text[hit_start:hit_end]
    if excerpt and actual != excerpt:
        raise EvidenceValidationError("retriever excerpt does not match immutable source text")
    return actual


def fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
