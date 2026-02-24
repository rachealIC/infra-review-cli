# src/infra_review_cli/core/ai/llm_client.py
"""
LLM client with provider chain: Claude (primary) → Gemini → OpenAI → graceful degradation.

No credentials are required — if all providers fail, the tool still works fully,
it just won't have AI-generated suggestions.
"""

import os
from dotenv import load_dotenv

load_dotenv()

_NO_AI = os.getenv("INFRA_REVIEW_NO_AI", "").lower() in ("true", "1", "yes")

# ---------------------------------------------------------------------------
# Claude (Anthropic) — primary provider
# ---------------------------------------------------------------------------
_anthropic_client = None
try:
    import anthropic as _anthropic_module
    _api_key = os.getenv("ANTHROPIC_API_KEY")
    if _api_key:
        _anthropic_client = _anthropic_module.Anthropic(api_key=_api_key)
except Exception:
    _anthropic_client = None

# ---------------------------------------------------------------------------
# Gemini — secondary provider
# ---------------------------------------------------------------------------
_gemini_model = None
try:
    import google.generativeai as genai
    _gemini_key = os.getenv("GEMINI_API_KEY")
    if _gemini_key:
        genai.configure(api_key=_gemini_key)
        _gemini_model = genai.GenerativeModel("gemini-2.5-flash")
except Exception:
    _gemini_model = None

# ---------------------------------------------------------------------------
# OpenAI — tertiary/fallback provider
# ---------------------------------------------------------------------------
_openai_client = None
try:
    from openai import OpenAI as _OpenAI
    _openai_key = os.getenv("OPENAI_API_KEY")
    if _openai_key:
        _openai_client = _OpenAI(api_key=_openai_key)
except Exception:
    _openai_client = None


# ---------------------------------------------------------------------------
# Provider call functions
# ---------------------------------------------------------------------------

def call_claude(prompt: str, model: str = "claude-3-5-haiku-20241022") -> str:
    """
    Call Claude (Anthropic). Raises RuntimeError if not configured.
    Uses haiku by default for cost efficiency; callers can override to sonnet/opus.
    """
    if not _anthropic_client:
        raise RuntimeError("Claude not configured — set ANTHROPIC_API_KEY.")
    message = _anthropic_client.messages.create(
        model=model,
        max_tokens=1024,
        system=(
            "You are a senior cloud infrastructure expert specialising in the "
            "AWS Well-Architected Framework. Your answers are concise, direct, "
            "and immediately actionable."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def call_gemini(prompt: str) -> str:
    """Call Gemini. Raises RuntimeError if not configured."""
    if not _gemini_model:
        raise RuntimeError("Gemini not configured — set GEMINI_API_KEY.")
    return _gemini_model.generate_content(prompt).text.strip()


def call_openai(prompt: str, model: str = "gpt-4o-mini") -> str:
    """Call OpenAI. Raises RuntimeError if not configured."""
    if not _openai_client:
        raise RuntimeError("OpenAI not configured — set OPENAI_API_KEY.")
    response = _openai_client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior cloud infrastructure expert specialising in the "
                    "AWS Well-Architected Framework. Your answers are concise, direct, "
                    "and immediately actionable."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def call_ai(prompt: str) -> str | None:
    """
    Try the full provider chain: Claude → Gemini → OpenAI.
    Returns the response string, or None if all providers fail or are unconfigured.
    This is the primary function all other AI modules should use.
    """
    if _NO_AI:
        return None

    for name, fn in [("Claude", call_claude), ("Gemini", call_gemini), ("OpenAI", call_openai)]:
        try:
            result = fn(prompt)
            if result:
                return result
        except Exception as e:
            # We catch all exceptions from providers to ensure the tool never crashes
            # because of an AI quota/network/config issue.
            continue
    return None


def ai_available() -> bool:
    """True if at least one AI provider is configured."""
    return any([_anthropic_client, _gemini_model, _openai_client])