"""Constrained simulated custodian for closed-loop synthetic-case replays.

This is a scenario-test adapter, not a replacement for a human respondent.
The model can select only supplied fixture item IDs and slot IDs. Python
validates both lists before any selected material is passed back through PIRIS.
"""
from __future__ import annotations

from typing import Any


_SYSTEM = """You are simulating a records custodian for a SYNTHETIC investigation.
Return JSON only with exactly these keys: selected_item_ids, answered_slot_ids.
Select only supplied item IDs that could help answer this specific request.
Select only supplied slot IDs that the selected material appears to address.
Do not write an answer, infer incident facts, invent documents, or select an
item merely because it shares a broad topic. Empty lists are valid."""


def select_fixture_response(model: Any, request: Any, slots: list[dict[str, str]],
                            available_items: list[dict[str, str]]) -> dict[str, Any]:
    """Ask the configured model to find a fixture response; enforce ID bounds."""
    payload = {
        "request": {
            "request_id": request.request_id,
            "kind": request.request_kind,
            "wording": request.wording,
            "target_ids": list(request.target_ids),
            "source_scope": list(request.source_scope),
            "entity_ids": list(request.entity_ids),
            "time_scope": request.time_scope,
            "record_types": list(request.record_types),
            "slots": slots,
        },
        "available_fixture_items": available_items,
        "warning": "These are synthetic fixture records, not authentic R3 evidence.",
    }
    result = model.ask("synthetic_custodian_response", _SYSTEM, payload)
    if not isinstance(result, dict) or set(result) != {"selected_item_ids", "answered_slot_ids"}:
        raise ValueError("custodian response must contain only selected_item_ids and answered_slot_ids")
    selected = result["selected_item_ids"]
    answered = result["answered_slot_ids"]
    allowed_items = {row["item_id"] for row in available_items}
    allowed_slots = {row["slot_id"] for row in slots}
    if (not isinstance(selected, list) or not all(isinstance(x, str) for x in selected)
            or len(selected) != len(set(selected)) or not set(selected) <= allowed_items):
        raise ValueError("custodian selected an unknown or duplicate fixture item ID")
    if (not isinstance(answered, list) or not all(isinstance(x, str) for x in answered)
            or len(answered) != len(set(answered)) or not set(answered) <= allowed_slots):
        raise ValueError("custodian selected an unknown or duplicate request slot ID")
    if answered and not selected:
        raise ValueError("custodian cannot mark slots answered without supplying a fixture item")
    return {"selected_item_ids": selected, "answered_slot_ids": answered}


__all__ = ["select_fixture_response"]
