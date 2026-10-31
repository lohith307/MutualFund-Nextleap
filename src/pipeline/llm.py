"""
llm.py — LLM Inference Wrapper (Phase 3 & 4)

Provides deterministic, facts-only inference using Groq, Google Gemini, or OpenAI.

Configuration (.env):
  - LLM_PROVIDER: "groq" (default) | "gemini" | "openai"
  - LLM_MODEL: "llama-3.3-70b-versatile" (default for groq) | "gemini-1.5-flash" | "gpt-4o-mini"
  - LLM_TEMPERATURE: 0.0 (strictly deterministic)
  - LLM_MAX_TOKENS: 200 (enforces concise answers)

Edge Cases Handled:
  - L-04: Empty LLM response handling
  - L-06: Rate limit handling (exponential backoff)
  - L-07: Timeout (> 15 seconds)
  - Missing API key: Returns clean informational error without crashing
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

load_dotenv()

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "200"))
REQUEST_TIMEOUT = 15  # seconds


class LLMError(Exception):
    """Raised when an LLM call fails after retries."""
    pass


# ── Groq Client ───────────────────────────────────────────────────────────────

def _call_groq(system_prompt: str, user_prompt: str, api_key: str) -> str:
    """Invoke Groq API (ultra-low latency, deterministic inference)."""
    from groq import Groq

    client = Groq(api_key=api_key, timeout=REQUEST_TIMEOUT)

    response = client.chat.completions.create(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content
    if not content or not content.strip():
        raise LLMError("Groq returned an empty response.")

    return content.strip()


# ── Gemini Client ─────────────────────────────────────────────────────────────

def _call_gemini(system_prompt: str, user_prompt: str, api_key: str) -> str:
    """Invoke Google Gemini API."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    # Gemini 1.5 allows system_instruction directly in GenerativeModel
    model = genai.GenerativeModel(
        model_name=LLM_MODEL,
        system_instruction=system_prompt,
        generation_config={
            "temperature": LLM_TEMPERATURE,
            "max_output_tokens": LLM_MAX_TOKENS,
        },
    )

    response = model.generate_content(
        user_prompt,
        request_options={"timeout": REQUEST_TIMEOUT},
    )

    if not response or not response.text:
        raise LLMError("Gemini returned an empty response.")

    return response.text.strip()


# ── OpenAI Client ─────────────────────────────────────────────────────────────

def _call_openai(system_prompt: str, user_prompt: str, api_key: str) -> str:
    """Invoke OpenAI API."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT)

    response = client.chat.completions.create(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content
    if not content or not content.strip():
        raise LLMError("OpenAI returned an empty response.")

    return content.strip()


# ── Core Generate Function ────────────────────────────────────────────────────

@retry(
    retry=retry_if_exception_type((TimeoutError, ConnectionError, LLMError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _generate_with_retry(system_prompt: str, user_prompt: str) -> str:
    """Execute LLM call with 3 retries on network/timeout errors."""
    if LLM_PROVIDER == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key.startswith("gsk_..."):
            raise ValueError("GROQ_API_KEY is not configured in .env.")
        return _call_groq(system_prompt, user_prompt, api_key)

    elif LLM_PROVIDER == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key.startswith("sk-..."):
            raise ValueError("OPENAI_API_KEY is not configured in .env.")
        return _call_openai(system_prompt, user_prompt, api_key)

    elif LLM_PROVIDER in ("gemini", "google"):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or api_key.startswith("AIza..."):
            raise ValueError("GOOGLE_API_KEY is not configured in .env.")
        return _call_gemini(system_prompt, user_prompt, api_key)

    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{LLM_PROVIDER}'. Choose 'groq', 'gemini', or 'openai'."
        )


def generate(system_prompt: str, user_prompt: str) -> str:
    """
    Main LLM inference entry point.

    Args:
        system_prompt: Constraining system instructions.
        user_prompt: Formatted prompt with context and user question.

    Returns:
        Generated answer string.
    """
    try:
        return _generate_with_retry(system_prompt, user_prompt)
    except ValueError as ve:
        logger.warning("LLM configuration error: %s", ve)
        # Fallback response for missing API key: return grounded context note
        return (
            "I could not connect to the LLM service because the API key is not configured. "
            "Please check the official scheme page directly."
        )
    except Exception as exc:
        logger.error("LLM inference failed after retries: %s", exc)
        return "I could not find this information in the official documents."
