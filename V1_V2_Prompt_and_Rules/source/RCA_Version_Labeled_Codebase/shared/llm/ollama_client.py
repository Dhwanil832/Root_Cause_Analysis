"""Native Ollama ``/api/chat`` adapter for the RCA model-client interface.

The adapter has no third-party dependencies and never falls back to fixtures.
It implements ``ask(task, system, payload)`` and returns a parsed JSON object,
matching the model port used by V1, V2, PIRIS, CFERP, SAHS, EWV3, and HERA1.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from .client import CallRecord, ModelFailure, parse_json

_JSON_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "null": lambda v: v is None,
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
}


def schema_errors(value, schema: dict, *, limit: int = 12) -> list[str]:
    """Check ``value`` against the JSON Schema subset used by RCA structured outputs.

    Supports ``type`` (including type lists), ``enum``, ``const``, ``required``,
    ``properties``, ``additionalProperties: false``, ``items``, and local
    ``#/$defs/...`` references. Returns up to ``limit`` path-prefixed messages;
    an empty list means the value conforms.
    """
    errors: list[str] = []

    def resolve(node: dict) -> dict:
        ref = node.get("$ref")
        if ref is None:
            return node
        target = schema
        for part in ref.removeprefix("#/").split("/"):
            target = target[part]
        return target

    def walk(item, node: dict, path: str) -> None:
        if len(errors) >= limit:
            return
        node = resolve(node)
        if "const" in node and item != node["const"]:
            errors.append(f"{path}: must equal {node['const']!r}")
            return
        if "enum" in node and item not in node["enum"]:
            errors.append(f"{path}: {item!r} is not one of {node['enum']!r}")
            return
        expected = node.get("type")
        if expected is not None:
            names = [expected] if isinstance(expected, str) else list(expected)
            if not any(_JSON_TYPES[name](item) for name in names):
                errors.append(f"{path}: expected {'|'.join(names)}, got {type(item).__name__}")
                return
        if isinstance(item, dict):
            props = node.get("properties", {})
            for key in node.get("required", ()):
                if key not in item:
                    errors.append(f"{path}: missing required field {key!r}")
            if node.get("additionalProperties") is False:
                for key in sorted(item.keys() - props.keys()):
                    errors.append(f"{path}: unexpected field {key!r}")
            for key, child in props.items():
                if key in item:
                    walk(item[key], child, f"{path}.{key}")
        elif isinstance(item, list) and "items" in node:
            for index, element in enumerate(item):
                walk(element, node["items"], f"{path}[{index}]")

    walk(value, schema, "$")
    return errors[:limit]


class PromptTooLarge(ModelFailure):
    """The prompt does not fit the context window; Ollama refused it rather than cut it."""

    def __init__(self, message: str, prompt_tokens: int | None = None, context_tokens: int | None = None):
        super().__init__(message)
        self.prompt_tokens = prompt_tokens
        self.context_tokens = context_tokens


def _context_overflow(detail: str) -> tuple[int | None, int | None] | None:
    """(prompt tokens, context tokens) when an HTTP 400 body is Ollama's context-size refusal."""
    if "exceed_context_size" not in detail and "exceeds the available context size" not in detail:
        return None
    found = {}
    for key in ("n_prompt_tokens", "n_ctx"):
        marker = detail.find(key)
        digits = "".join(ch for ch in detail[marker + len(key):marker + len(key) + 16] if ch.isdigit()) if marker >= 0 else ""
        found[key] = int(digits) if digits else None
    return found["n_prompt_tokens"], found["n_ctx"]


class OllamaChatModel:
    """Synchronous client for a model served by a local Ollama instance.

    Args:
        model: Exact local model tag, as shown by ``ollama list``.
        base_url: Ollama host origin, such as ``http://localhost:11434``.
        timeout: Per-request timeout in seconds.
        response_format: ``json_object`` requests Ollama JSON mode. ``off``
            omits the format field while still requiring a JSON object response.
        retries: Number of bounded retries for transient HTTP/network or JSON
            formatting failures.
        temperature: Generation temperature passed through Ollama options.
        keep_alive: Optional Ollama model keep-alive duration, for example
            ``5m``. ``None`` leaves the server default in effect.
        task_schemas: Optional ``{task: JSON Schema}``. A task listed here is
            sent with its schema as Ollama's structured-output ``format`` and
            every reply is checked against it before being returned.
        schema_retries: Bounded retries, for schema-governed tasks only, when a
            reply is empty, not JSON, or violates the schema. Each retry shows
            the model its prior reply and the validation errors. A reply that
            still fails raises ``ModelFailure``; nothing is repaired or filled in.
        max_raw_records: Cap on retained ``raw_responses`` entries.
        num_ctx: Optional context window (tokens) passed as ``options.num_ctx``.
            ``None`` leaves the server default, which is often 4096 regardless
            of the model's maximum; a prompt that fills it leaves no room to
            generate (``done_reason == "length"``).
        truncate_prompt: Ollama's default is to cut a prompt longer than the
            context window down to its tail, silently dropping the system
            instructions. ``False`` (the default here) sends ``truncate: false``
            so Ollama refuses instead, and the call raises ``PromptTooLarge``
            with the exact prompt token count. It is not retried.
        think: Optional reasoning setting sent as Ollama's ``think`` field:
            ``"low"``, ``"medium"`` or ``"high"`` for gpt-oss, ``True``/``False``
            for other thinking models. ``None`` leaves the model's default.

    A payload key ``previous_response_rejected`` (``reason``, ``previous_reply``,
    ``instruction``), which HERA adds when it re-asks after its own validation
    rejects a reply, is not sent inside the JSON message. It is delivered as chat
    turns: the model's earlier reply as an assistant message, then the rejection
    as a user message.

    ``raw_responses`` holds one entry per HTTP attempt: the full decoded
    Ollama reply (``message.content``, ``message.thinking``, ``done``,
    ``done_reason``, timing and token counts), the outcome, and any validation
    errors, so a rejected reply can be diagnosed after the fact.
    """

    TRANSIENT_HTTP_CODES = {408, 429, 500, 502, 503, 504}

    def __init__(self, model: str, base_url: str | None = None, *,
                 timeout: float = 300, response_format: str = "json_object",
                 retries: int = 1, temperature: float | None = 0.0,
                 keep_alive: str | None = None,
                 task_schemas: dict[str, dict] | None = None,
                 schema_retries: int = 2, max_raw_records: int = 200,
                 num_ctx: int | None = None, truncate_prompt: bool = False,
                 think: str | bool | None = None):
        if not isinstance(model, str) or not model.strip():
            raise ModelFailure("Set an explicit Ollama model tag (for example, one shown by `ollama list`)")
        host = (base_url or os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        if host.endswith("/api"):
            host = host[:-4]
        if not host.startswith(("http://", "https://")):
            raise ModelFailure("Ollama base URL must start with http:// or https://")
        if retries < 0 or schema_retries < 0:
            raise ModelFailure("retries and schema_retries must be non-negative")
        self.model = model.strip()
        self.base_url = host
        self.timeout = float(timeout)
        self.response_format = response_format
        self.retries = int(retries)
        self.temperature = temperature
        self.keep_alive = keep_alive
        self.provider = "ollama_native"
        self.task_schemas = dict(task_schemas or {})
        self.schema_retries = int(schema_retries)
        self.think = think
        self.max_raw_records = int(max_raw_records)
        self.num_ctx = num_ctx
        self.truncate_prompt = bool(truncate_prompt)
        self.calls: list[CallRecord] = []
        self.raw_responses: list[dict] = []
        self.http_attempts = 0

    @property
    def chat_url(self) -> str:
        return f"{self.base_url}/api/chat"

    @property
    def tags_url(self) -> str:
        return f"{self.base_url}/api/tags"

    def list_models(self) -> tuple[str, ...]:
        """Return locally installed model tags from Ollama's ``/api/tags``."""
        request = urllib.request.Request(self.tags_url, headers={"Accept": "application/json"}, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read(2_000_000))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise ModelFailure(f"Cannot reach Ollama at {self.base_url}: {type(exc).__name__}: {exc}") from exc
        rows = payload.get("models", ()) if isinstance(payload, dict) else ()
        return tuple(str(row.get("name", "")) for row in rows
                     if isinstance(row, dict) and row.get("name"))

    def check_model(self) -> tuple[str, ...]:
        """Check that Ollama is reachable and this exact model tag is present."""
        models = self.list_models()
        if self.model not in models:
            visible = ", ".join(models) if models else "(no models installed)"
            raise ModelFailure(f"Ollama model {self.model!r} is not installed; local models: {visible}")
        return models

    def _remember(self, record: dict) -> None:
        self.raw_responses.append(record)
        del self.raw_responses[:-self.max_raw_records]

    def ask(self, task: str, system: str, payload: dict) -> dict:
        schema = self.task_schemas.get(task)
        rejected = payload.get("previous_response_rejected") if isinstance(payload, dict) else None
        if isinstance(rejected, dict):
            payload = {key: value for key, value in payload.items() if key != "previous_response_rejected"}
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
        ]
        if isinstance(rejected, dict):
            if rejected.get("previous_reply") is not None:
                messages.append({"role": "assistant", "content": json.dumps(
                    rejected["previous_reply"], ensure_ascii=False, default=str)[:4000]})
            messages.append({"role": "user", "content": (
                f"That response was rejected: {rejected.get('reason', 'it failed validation')}. "
                f"{rejected.get('instruction', 'Return one corrected JSON object.')}")})
        began = time.monotonic()
        last_error = "unknown error"
        feedback: list[dict] = []
        transient_used = content_used = 0
        content_budget = self.schema_retries if schema is not None else self.retries
        format_kind = "schema" if schema is not None else (
            "json" if self.response_format in {"json_object", "json"} else "none")
        attempt = 0
        while True:
            attempt += 1
            body: dict = {
                "model": self.model,
                "messages": messages + feedback,
                "stream": False,
                "options": {},
            }
            if not self.truncate_prompt:
                body["truncate"] = False
            if schema is not None:
                body["format"] = schema
            elif format_kind == "json":
                body["format"] = "json"
            if self.temperature is not None:
                body["options"]["temperature"] = self.temperature
            if self.num_ctx is not None:
                body["options"]["num_ctx"] = int(self.num_ctx)
            if not body["options"]:
                body.pop("options")
            if self.keep_alive is not None:
                body["keep_alive"] = self.keep_alive
            if self.think is not None:
                body["think"] = self.think
            request = urllib.request.Request(
                self.chat_url,
                data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST",
            )
            self.http_attempts += 1
            record: dict = {"task": task, "attempt": attempt, "model": self.model,
                            "format": format_kind, "num_ctx": self.num_ctx,
                            "outcome": None, "errors": []}
            self._remember(record)
            transient = False
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    received = json.loads(response.read(5_000_000))
                message = received["message"]
                content, thinking = message.get("content"), message.get("thinking")
                record.update(
                    http_status=200, response=received,
                    content_chars=len(content) if isinstance(content, str) else 0,
                    thinking_chars=len(thinking) if isinstance(thinking, str) else 0,
                )
                try:
                    parsed = parse_json(content)
                except ValueError as exc:
                    empty = not (isinstance(content, str) and content.strip())
                    record.update(outcome="empty_content" if empty else "invalid_json",
                                  errors=[str(exc)])
                    last_error = (
                        f"Invalid Ollama response: {exc} (done_reason={received.get('done_reason')!r}, "
                        f"content_chars={record['content_chars']}, thinking_chars={record['thinking_chars']})"
                    )
                    nudge = ("The prior response had no message content. Put the complete JSON object in the "
                             "message content itself, not in reasoning."
                             if empty and schema is not None else
                             "The prior response was not a valid JSON object. Return one complete JSON object "
                             "only, following the requested fields and constraints.")
                    failed_content = content if isinstance(content, str) else ""
                else:
                    problems = schema_errors(parsed, schema) if schema is not None else []
                    if not problems:
                        tokens = {
                            key: received[key]
                            for key in ("prompt_eval_count", "eval_count", "total_duration",
                                        "load_duration", "prompt_eval_duration", "eval_duration")
                            if key in received
                        }
                        record["outcome"] = "accepted"
                        self.calls.append(CallRecord(
                            task=task, model=self.model, provider=self.provider,
                            actual_call_performed=True,
                            latency_seconds=round(time.monotonic() - began, 3),
                            tokens=tokens, output=parsed,
                        ))
                        return parsed
                    record.update(outcome="schema_invalid", errors=problems)
                    last_error = "Response violated the task schema: " + "; ".join(problems[:5])
                    nudge = ("The prior response violated the required JSON Schema: " + "; ".join(problems[:8])
                             + ". Return one complete JSON object that conforms exactly to the schema, "
                             "with no extra or missing fields.")
                    failed_content = content
                if content_used >= content_budget:
                    break
                content_used += 1
                feedback = [{"role": "assistant", "content": failed_content[:4000]},
                            {"role": "user", "content": nudge}] if failed_content else [
                            {"role": "user", "content": nudge}]
                continue
            except urllib.error.HTTPError as exc:
                detail = exc.read(1200).decode("utf-8", "replace")
                last_error = f"HTTP {exc.code}: {detail}"
                record.update(outcome=f"http_error:{exc.code}", http_status=exc.code,
                              errors=[detail])
                overflow = _context_overflow(detail) if exc.code == 400 else None
                if overflow is not None:
                    prompt_tokens, context_tokens = overflow
                    record.update(outcome="prompt_exceeds_context", prompt_tokens=prompt_tokens,
                                  context_tokens=context_tokens)
                    raise PromptTooLarge(
                        f"Ollama/{self.model} {task}: prompt of {prompt_tokens} tokens exceeds the "
                        f"{context_tokens}-token context window; refused, not truncated",
                        prompt_tokens, context_tokens) from exc
                transient = exc.code in self.TRANSIENT_HTTP_CODES
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                record.update(outcome="transport_error", errors=[last_error])
                transient = True
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                last_error = f"Invalid Ollama response: {exc}"
                record.update(outcome="malformed_response", errors=[last_error])
                transient = True
            if not transient or transient_used >= self.retries:
                break
            time.sleep(min(2 ** transient_used, 3))
            transient_used += 1
        raise ModelFailure(
            f"Ollama/{self.model} {task} call failed after {attempt} HTTP attempts: {last_error}"
        )
