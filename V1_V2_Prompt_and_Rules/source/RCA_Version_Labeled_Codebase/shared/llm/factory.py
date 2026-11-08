"""Construct one model port for every role from the shared run configuration."""
from __future__ import annotations

from .client import ChatCompletionsModel


def create_model_client(*, provider: str, model: str, base_url: str | None = None,
                        timeout: float = 120, response_format: str = "json_object",
                        retries: int = 1, temperature: float | None = 0.0,
                        keep_alive: str | None = None,
                        task_schemas: dict | None = None, schema_retries: int = 2,
                        num_ctx: int | None = None, think: str | bool | None = None):
    """Create a native Ollama or OpenAI-compatible chat client.

    ``ollama_native`` speaks Ollama's ``/api/chat`` protocol. Other provider
    names retain the existing OpenAI-compatible ``/chat/completions`` path.
    ``task_schemas``, ``schema_retries``, ``num_ctx`` and ``think`` apply to the native Ollama client only.
    """
    if provider in {"ollama_native", "ollama-native"}:
        from .ollama_client import OllamaChatModel
        # The legacy profiles use ``off`` to disable OpenAI's response_format
        # parameter. Every RCA role still requires a JSON object, and native
        # Ollama supports its own JSON mode, so translate that legacy setting.
        ollama_format = "json_object" if response_format in {None, "", "off"} else response_format
        return OllamaChatModel(
            model=model, base_url=base_url, timeout=timeout,
            response_format=ollama_format, retries=retries,
            temperature=temperature, keep_alive=keep_alive,
            task_schemas=task_schemas, schema_retries=schema_retries,
            num_ctx=num_ctx, think=think,
        )
    compatible_provider = "ollama" if provider == "ollama-compatible" else provider
    return ChatCompletionsModel(
        provider=compatible_provider, model=model, base_url=base_url,
        timeout=timeout, response_format=response_format, retries=retries,
    )
