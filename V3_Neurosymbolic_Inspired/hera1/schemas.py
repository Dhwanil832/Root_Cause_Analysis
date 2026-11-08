"""JSON Schemas for HERA model replies, for providers with structured output.

Field names and enums mirror ``validate_statement_batch``,
``validate_comparison`` and the request-review checks in ``Hera1Engine``. A schema constrains the reply's shape only; those
validators still decide whether a quote is located in the packet, whether
statement IDs resolve, and what a finding may claim.
"""
from __future__ import annotations

from typing import Any

STATEMENT_KINDS = ["incident_observation", "reported_event", "incident_causal_statement",
                   "general_mechanism", "procedure", "hypothetical", "other"]
STATEMENT_MODALITIES = ["asserted", "reported", "measured", "conditional", "possible",
                        "negated", "inferred", "unclear"]
FINDING_RELATIONS = ["supports", "weakens", "contradicts", "does_not_address",
                     "insufficient_or_unclear"]
_ALIGNMENT = ["match", "mismatch", "unknown"]

_STATEMENT_FIELDS: dict[str, Any] = {
    "statement_id": {"type": "string"},
    "material_id": {"type": "string"},
    "source_id": {"type": "string"},
    "source_version": {"type": "string"},
    "representation_id": {"type": "string"},
    "quote": {"type": "string"},
    "start_offset": {"type": "integer"},
    "kind": {"enum": STATEMENT_KINDS},
    "modality": {"enum": STATEMENT_MODALITIES},
    "scope": {"type": "string"},
    "timing": {"type": "string"},
}

EXTRACT_STATEMENTS_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False, "required": ["statements"],
    "properties": {"statements": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": list(_STATEMENT_FIELDS), "properties": _STATEMENT_FIELDS,
    }}},
}

_FINDING_FIELDS: dict[str, Any] = {
    "relation": {"enum": FINDING_RELATIONS},
    "statement_ids": {"type": "array", "items": {"type": "string"}},
    "rationale": {"type": "string"},
    "inference_bridge": {"type": "string"},
    "relevance_status": {"enum": ["direct", "indirect", "unrelated", "uncertain"]},
    "scope_alignment": {"enum": _ALIGNMENT},
    "time_alignment": {"enum": _ALIGNMENT},
}

COMPARE_STATEMENTS_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False, "required": ["parts"],
    "properties": {"parts": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["part_id", "findings"],
        "properties": {
            "part_id": {"type": "string"},
            "findings": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "required": list(_FINDING_FIELDS), "properties": _FINDING_FIELDS,
            }},
        },
    }}},
}

_REQUEST_REVIEW_FIELDS: dict[str, Any] = {
    "disposition": {"enum": ["eligible", "revise", "not_eligible"]},
    "rationale": {"type": "string"},
    "existing_evidence_status": {"enum": ["resolved", "unresolved", "uncertain"]},
    "existing_evidence_rationale": {"type": "string"},
    "proportionality": {"enum": ["proportionate", "disproportionate", "uncertain"]},
    "revision_feedback": {"type": "string"},
    "revised_request": {"type": "string"},
}

# The rule that revision_feedback/revised_request stay empty unless the
# disposition is `revise` is conditional; the engine's Python check keeps it.
REVIEW_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": list(_REQUEST_REVIEW_FIELDS), "properties": _REQUEST_REVIEW_FIELDS,
}

HERA_TASK_SCHEMAS: dict[str, dict[str, Any]] = {
    "extract_statements": EXTRACT_STATEMENTS_SCHEMA,
    "compare_statements": COMPARE_STATEMENTS_SCHEMA,
    "review_request": REVIEW_REQUEST_SCHEMA,
}
