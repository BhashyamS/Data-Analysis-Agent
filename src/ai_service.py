"""Gemini service for Analytics Copilot."""

from __future__ import annotations

from google import genai
from google.genai import types


DEFAULT_MODEL = "gemini-2.5-flash"


class AIServiceError(RuntimeError):
    """Raised when Gemini cannot complete a request."""


def generate_ai_response(
    *,
    api_key: str,
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    max_output_tokens: int = 2500,
    response_mime_type: str | None = None,
) -> str:
    """Generate one Gemini response."""
    cleaned_key = api_key.strip()

    if not cleaned_key:
        raise AIServiceError("A Gemini API key is required.")

    try:
        config_kwargs = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }

        if response_mime_type:
            config_kwargs["response_mime_type"] = response_mime_type

        client = genai.Client(api_key=cleaned_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        text = getattr(response, "text", None)

        if not text or not text.strip():
            raise AIServiceError("Gemini returned an empty response.")

        return text.strip()

    except AIServiceError:
        raise
    except Exception as exc:
        raise AIServiceError(f"Gemini request failed: {exc}") from exc
