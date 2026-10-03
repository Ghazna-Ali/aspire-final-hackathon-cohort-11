"""
Free-tier multi-provider LLM manager for CareerOps AI (Oct 2026).

- Only free-tier models
- API key presence + basic format/length checks
- Default model prefers the first available Gemini, then Groq, etc.
"""
import os
import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import streamlit as st
from crewai import LLM


PLACEHOLDER_VALUES = {
    "",
    "paste your api key here",
    "paste_your_api_key_here",
    "your_api_key_here",
    "your-api-key-here",
    "changeme",
    "change_me",
    "null",
    "none",
}


# ------------------------------------------------------------
# KEY FORMAT RULES (length + optional prefix)
# These are soft checks — they catch common mistakes, not every invalid key.
# ------------------------------------------------------------
KEY_RULES = {
    "GEMINI_API_KEY": {
        "min_len": 30,
        "max_len": 60,
        "prefix": "AIza",          # Google API keys usually start with AIza
        "hint": "Google keys usually start with 'AIza' and are about 39 characters.",
    },
    "GROQ_API_KEY": {
        "min_len": 40,
        "max_len": 120,
        "prefix": "gsk_",          # Groq keys start with gsk_
        "hint": "Groq keys usually start with 'gsk_' and are longer than 40 characters.",
    },
    "OPENROUTER_API_KEY": {
        "min_len": 40,
        "max_len": 200,
        "prefix": "sk-or-",        # OpenRouter keys start with sk-or-
        "hint": "OpenRouter keys usually start with 'sk-or-' and are long tokens.",
    },
    "MISTRAL_API_KEY": {
        "min_len": 20,
        "max_len": 80,
        "prefix": None,            # format varies
        "hint": "Mistral keys are typically 32+ characters. Check console.mistral.ai.",
    },
}


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    display_name: str
    model_id: str
    secret_key: str
    tier: str
    notes: str = ""

    @property
    def crewai_model(self) -> str:
        return self.model_id


MODEL_CATALOG: Dict[str, ModelSpec] = {
    # ---------- Google Gemini (native, free tier) ----------
    "gemini_3_8_flash": ModelSpec(
        provider="gemini",
        display_name="Gemini 3.8 Flash",
        model_id="gemini/gemini-3.8-flash",
        secret_key="GEMINI_API_KEY",
        tier="Free tier",
        notes="Google AI Studio free tier. Native CrewAI.",
    ),
    "gemini_3_5_flash_lite": ModelSpec(
        provider="gemini",
        display_name="Gemini 3.5 Flash-Lite",
        model_id="gemini/gemini-3.5-flash-lite",
        secret_key="GEMINI_API_KEY",
        tier="Free tier",
        notes="Fast Gemini free-tier model. Native CrewAI.",
    ),
    "gemini_2_5_flash": ModelSpec(
        provider="gemini",
        display_name="Gemini 2.5 Flash",
        model_id="gemini/gemini-2.5-flash",
        secret_key="GEMINI_API_KEY",
        tier="Free tier",
        notes="Still free for many projects. Native CrewAI.",
    ),
    # ---------- Groq ----------
    "groq_gpt_oss_120b": ModelSpec(
        provider="groq",
        display_name="Groq GPT-OSS 120B",
        model_id="groq/openai/gpt-oss-120b",
        secret_key="GROQ_API_KEY",
        tier="Free tier",
        notes="Very fast. Free plan rate limits apply.",
    ),
    "groq_gpt_oss_20b": ModelSpec(
        provider="groq",
        display_name="Groq GPT-OSS 20B",
        model_id="groq/openai/gpt-oss-20b",
        secret_key="GROQ_API_KEY",
        tier="Free tier",
        notes="Lighter Groq free-tier model.",
    ),
    "groq_qwen_3_8_27b": ModelSpec(
        provider="groq",
        display_name="Groq Qwen3.8 27B",
        model_id="groq/qwen/qwen3.8-27b",
        secret_key="GROQ_API_KEY",
        tier="Free tier",
        notes="Strong open model on Groq free tier.",
    ),
    # ---------- OpenRouter free ----------
    "openrouter_qwen_3_8_27b": ModelSpec(
        provider="openrouter",
        display_name="OpenRouter Qwen3.8 27B (free)",
        model_id="openrouter/qwen/qwen3.8-27b:free",
        secret_key="OPENROUTER_API_KEY",
        tier="Free tier",
        notes=":free route. Daily request limits apply.",
    ),
    "openrouter_gemma_4_31b": ModelSpec(
        provider="openrouter",
        display_name="OpenRouter Gemma 4 31B (free)",
        model_id="openrouter/google/gemma-4-31b-it:free",
        secret_key="OPENROUTER_API_KEY",
        tier="Free tier",
        notes="Strong free open model via OpenRouter.",
    ),
    "openrouter_nemotron_3_super": ModelSpec(
        provider="openrouter",
        display_name="OpenRouter Nemotron 3 Super (free)",
        model_id="openrouter/nvidia/nemotron-3-super-120b-a12b:free",
        secret_key="OPENROUTER_API_KEY",
        tier="Free tier",
        notes="NVIDIA open MoE model, free on OpenRouter.",
    ),
    # ---------- Mistral ----------
    "mistral_small": ModelSpec(
        provider="mistral",
        display_name="Mistral Small (free)",
        model_id="mistral/mistral-small-latest",
        secret_key="MISTRAL_API_KEY",
        tier="Free Experiment",
        notes="Mistral Experiment plan. Rate-limited.",
    ),
}

# Preferred default order when multiple keys are valid
DEFAULT_MODEL_PRIORITY = [
    "gemini_3_8_flash",
    "gemini_3_5_flash_lite",
    "gemini_2_5_flash",
    "groq_gpt_oss_120b",
    "groq_gpt_oss_20b",
    "groq_qwen_3_8_27b",
    "openrouter_qwen_3_8_27b",
    "openrouter_gemma_4_31b",
    "mistral_small",
]


def _read_secret_or_env(name: str) -> Optional[str]:
    value = None
    try:
        value = st.secrets.get(name)
    except Exception:
        pass
    if value is None:
        value = os.getenv(name)
    if value is None:
        return None
    value = str(value).strip()
    if value.lower() in PLACEHOLDER_VALUES:
        return None
    return value


def get_api_key(secret_key: str) -> Optional[str]:
    return _read_secret_or_env(secret_key)


def validate_api_key(secret_key: str, value: Optional[str] = None) -> Tuple[bool, str]:
    """
    Check that a key exists and roughly matches expected length/prefix.

    Returns (is_valid, message).
    """
    if value is None:
        value = get_api_key(secret_key)

    if not value:
        return False, f"{secret_key} is missing. Add it in Streamlit Secrets."

    rules = KEY_RULES.get(secret_key)
    if not rules:
        # Unknown key type — only require non-empty
        if len(value) < 10:
            return False, f"{secret_key} looks too short ({len(value)} chars)."
        return True, f"{secret_key} looks present ({len(value)} chars)."

    length = len(value)
    min_len = rules["min_len"]
    max_len = rules["max_len"]
    prefix = rules.get("prefix")
    hint = rules.get("hint", "")

    if length < min_len or length > max_len:
        return (
            False,
            f"{secret_key} length looks wrong ({length} chars). "
            f"Expected about {min_len}–{max_len}. {hint}",
        )

    if prefix and not value.startswith(prefix):
        return (
            False,
            f"{secret_key} should start with '{prefix}' but starts with "
            f"'{value[: min(8, length)]}...'. {hint}",
        )

    # Extra soft check: mostly printable ASCII
    if not re.match(r"^[\x21-\x7E]+$", value):
        return False, f"{secret_key} contains unexpected characters. {hint}"

    return True, f"{secret_key} format looks OK ({length} chars)."


def is_model_available(model_key: str) -> bool:
    """True only if the key is present AND passes format/length checks."""
    if model_key not in MODEL_CATALOG:
        return False
    spec = MODEL_CATALOG[model_key]
    ok, _ = validate_api_key(spec.secret_key)
    return ok


def get_key_status_message(model_key: str) -> str:
    """Human-readable status for the selected model’s key."""
    if model_key not in MODEL_CATALOG:
        return "Unknown model."
    spec = MODEL_CATALOG[model_key]
    ok, message = validate_api_key(spec.secret_key)
    return message


def available_model_keys():
    return [key for key in MODEL_CATALOG if is_model_available(key)]


def unavailable_model_keys():
    return [key for key in MODEL_CATALOG if not is_model_available(key)]


def default_model_key() -> str:
    """
    Prefer the first model whose key is valid, following DEFAULT_MODEL_PRIORITY.
    Falls back to the first catalog entry if none are ready.
    """
    for key in DEFAULT_MODEL_PRIORITY:
        if key in MODEL_CATALOG and is_model_available(key):
            return key
    # Fallback: first catalog key (UI will show it as missing key)
    return next(iter(MODEL_CATALOG.keys()))


def model_label(model_key: str) -> str:
    spec = MODEL_CATALOG[model_key]
    if is_model_available(model_key):
        return f"🟢 {spec.display_name}  •  {spec.tier}"
    return f"⚪ {spec.display_name}  •  API key missing/invalid"


def build_llm(model_key: str) -> LLM:
    if model_key not in MODEL_CATALOG:
        raise ValueError(f"Unknown model: {model_key}")

    spec = MODEL_CATALOG[model_key]
    api_key = get_api_key(spec.secret_key)
    ok, message = validate_api_key(spec.secret_key, api_key)

    if not ok:
        raise ValueError(message)

    kwargs = {
        "model": spec.crewai_model,
        "api_key": api_key,
        "temperature": 0.2,
    }
    if spec.provider == "openrouter":
        kwargs["base_url"] = "https://openrouter.ai/api/v1"

    return LLM(**kwargs)


def get_model_status_rows():
    rows = []
    for key, spec in MODEL_CATALOG.items():
        ok, msg = validate_api_key(spec.secret_key)
        rows.append(
            {
                "model_key": key,
                "provider": spec.provider,
                "model": spec.display_name,
                "tier": spec.tier,
                "configured": ok,
                "secret": spec.secret_key,
                "status": msg,
            }
        )
    return rows


def configure_agents(agents: Dict[str, object], model_key: str) -> None:
    llm = build_llm(model_key)
    for agent in agents.values():
        agent.llm = llm


def selected_model_info(model_key: str) -> ModelSpec:
    return MODEL_CATALOG[model_key]
