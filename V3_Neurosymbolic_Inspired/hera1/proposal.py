"""Adapter for any model client exposing ask(task, system, payload)."""
from __future__ import annotations

from typing import Any


class AskModelAdapter:
    """Keep provider/runtime selection outside HERA1 and preserve call auditing."""

    def __init__(self, client: Any) -> None:
        if not callable(getattr(client, "ask", None)):
            raise TypeError("model client must expose ask(task, system, payload)")
        self.client = client
        self.calls_made = 0

    def ask(self, task: str, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls_made += 1
        result = self.client.ask(task, system, payload)
        if not isinstance(result, dict):
            raise ValueError("model client returned a non-object response")
        return result
