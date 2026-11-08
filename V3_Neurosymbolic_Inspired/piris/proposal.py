"""Optional adapter for archive-style structured LLM calls."""
from __future__ import annotations

import json

from .contracts import InterpretationRequest, ItemSuggestion, RequestReference


_TASK = "suggest_intake_metadata"
_SYSTEM = """You are a metadata helper for an investigation intake pipeline.
Return JSON only with this shape:
{"items":[{"item_id":"...","suggested_kind":"...","request_ids":["..."],"note":"..."}]}
Use only supplied item IDs and request IDs. Suggest a request link only when the
submission text itself gives a plausible relationship. If unclear, return no
request_ids. Keep suggested_kind open-ended; use other or unknown when needed.
Do not judge whether any document is relevant, answers a question, supports or
contradicts a hypothesis, or establishes an incident fact. Extract metadata only."""


class AskIntakeInterpreter:
    """Wraps a callable ``ask(task, system, payload)`` model client."""
    version = "ask-intake-interpreter-1"

    def __init__(self, ask) -> None:
        self.ask = ask

    def interpret(self, items: tuple[InterpretationRequest, ...],
                  requests: tuple[RequestReference, ...]) -> tuple[ItemSuggestion, ...]:
        payload = {
            "items": [{
                "item_id": item.item_id,
                "filename": item.filename,
                "media_type": item.media_type,
                "declared_kind": item.declared_kind,
                "extracted_text": item.extracted_text,
            } for item in items],
            "open_requests": [{"request_id": r.request_id, "description": r.description}
                              for r in requests],
        }
        raw = self.ask(_TASK, _SYSTEM, payload)
        if isinstance(raw, str):
            raw = json.loads(raw)
        if not isinstance(raw, dict) or set(raw) != {"items"} or not isinstance(raw["items"], list):
            raise ValueError("interpreter response must contain only an items list")
        suggestions = []
        for record in raw["items"]:
            if not isinstance(record, dict) or set(record) != {
                "item_id", "suggested_kind", "request_ids", "note"
            }:
                continue
            if not isinstance(record["item_id"], str) or not isinstance(record["suggested_kind"], str):
                continue
            if not isinstance(record["request_ids"], list) or not all(
                isinstance(x, str) for x in record["request_ids"]
            ):
                continue
            if not isinstance(record["note"], str):
                continue
            suggestions.append(ItemSuggestion(
                record["item_id"], record["suggested_kind"],
                tuple(record["request_ids"]), record["note"],
            ))
        return tuple(suggestions)

