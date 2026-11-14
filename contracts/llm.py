from __future__ import annotations

import json
import os
from typing import Any, Type

from pydantic import BaseModel, ValidationError


class LLMError(RuntimeError):
    """Raised when the LLM call fails or cannot produce valid JSON."""


def _strip_code_fences(value: str) -> str:
    text = value.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


def call_llm(
    system: str,
    user: str,
    schema: type[BaseModel],
    mock: BaseModel | dict | None = None,
) -> BaseModel:
    """Call the configured LLM or return a local mock object validated against the schema."""

    if os.getenv("USE_MOCK_LLM") == "1":
        if mock is None:
            raise ValueError("Provide a mock= for offline mode")
        payload = mock.model_dump(mode="json") if isinstance(mock, BaseModel) else mock
        return schema.model_validate(payload)

    provider = (os.getenv("LLM_PROVIDER") or "anthropic").strip().lower()
    if provider not in {"anthropic", "openai"}:
        raise LLMError(f"Unsupported LLM_PROVIDER: {provider}")

    api_key = os.getenv("ANTHROPIC_API_KEY") if provider == "anthropic" else os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("LLM_MODEL")
    if not api_key or not model_name:
        raise LLMError("LLM_MODEL and API key must be configured for live mode.")

    if provider == "anthropic":
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - environment guard
            raise LLMError("anthropic package is not installed") from exc

        client = anthropic.Anthropic(api_key=api_key, timeout=30.0)
        prompt = f"{system}\n\n{user}\n\nReturn JSON only matching this schema:\n{json.dumps(schema.model_json_schema(), separators=(',', ':'))}"
        response = client.messages.create(
            model=model_name,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content
        text = "".join(part.text for part in content if getattr(part, "type", None) == "text")
    else:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - environment guard
            raise LLMError("openai package is not installed") from exc

        client = OpenAI(api_key=api_key, timeout=30.0)
        prompt = f"{system}\n\n{user}\n\nReturn JSON only matching this schema:\n{json.dumps(schema.model_json_schema(), separators=(',', ':'))}"
        response = client.responses.create(
            model=model_name,
            input=prompt,
        )
        text = getattr(response, "output_text", "") or ""

    if not text:
        raise LLMError("LLM returned no text.")

    for attempt in range(2):
        payload_text = _strip_code_fences(text)
        try:
            parsed = json.loads(payload_text)
            return schema.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as exc:
            if attempt == 1:
                raise LLMError(f"LLM output was not valid for {schema.__name__}: {exc}") from exc
            text = (
                f"{payload_text}\n\nPrevious attempt failed: {exc}. "
                "Return only valid JSON matching the provided schema."
            )
            if provider == "anthropic":
                response = client.messages.create(
                    model=model_name,
                    max_tokens=2048,
                    system=system,
                    messages=[{"role": "user", "content": text}],
                )
                content = response.content
                text = "".join(part.text for part in content if getattr(part, "type", None) == "text")
            else:
                response = client.responses.create(model=model_name, input=text)
                text = getattr(response, "output_text", "") or ""

    raise LLMError(f"LLM output was not valid for {schema.__name__}.")
