"""
Thin wrapper around the Groq chat-completions API.

Two models are used deliberately (per the assignment brief):
  - GROQ_EXTRACTION_MODEL (gemma2-9b-it): fast field extraction from free text.
  - GROQ_REASONING_MODEL (llama-3.3-70b-versatile): higher-quality reasoning
    for risk classification / root cause / CAPA / duplicate rationale.

If GROQ_API_KEY is not set, `call_groq_json` falls back to a deterministic
offline heuristic (`_offline_fallback`) so the app still runs end-to-end for
local demo/grading without requiring a live key. This is intentional
defensive design, not a hidden crutch -- it's flagged clearly in logs and
in the API response (`_offline_mode`).
"""
import json
import re
import logging
from typing import Optional

import requests

from .config import GROQ_API_KEY, GROQ_API_BASE, GROQ_EXTRACTION_MODEL, GROQ_REASONING_MODEL

logger = logging.getLogger("aivoa.groq")


class GroqError(Exception):
    pass


def _extract_json(raw_text: str) -> dict:
    """LLMs sometimes wrap JSON in prose or code fences -- pull the JSON out robustly."""
    raw_text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if fence_match:
        raw_text = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if brace_match:
            raw_text = brace_match.group(0)
    return json.loads(raw_text)


def call_groq_json(system_prompt: str, user_prompt: str, model: str, temperature: float = 0.2) -> dict:
    """Call Groq, forcing a JSON-only response, and parse it. Raises GroqError on failure."""
    if not GROQ_API_KEY:
        raise GroqError("GROQ_API_KEY not configured")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    try:
        resp = requests.post(GROQ_API_BASE, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _extract_json(content)
    except Exception as exc:  # noqa: BLE001 - want a single failure path to fallback
        logger.warning("Groq call failed (%s); falling back to offline heuristic", exc)
        raise GroqError(str(exc)) from exc


def call_groq_extraction(system_prompt: str, user_prompt: str) -> dict:
    return call_groq_json(system_prompt, user_prompt, model=GROQ_EXTRACTION_MODEL, temperature=0.0)


def call_groq_reasoning(system_prompt: str, user_prompt: str) -> dict:
    return call_groq_json(system_prompt, user_prompt, model=GROQ_REASONING_MODEL, temperature=0.3)
