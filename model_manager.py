"""
Free-tier multi-provider LLM manager for CareerOps AI (Oct 2026).

Only providers with a real no-card free tier:
  - Google Gemini
  - Groq
  - Cerebras

OpenRouter and Mistral removed (limited / effectively paid for real use).
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
# KEY FORMAT RULES (soft checks)
# ------------------------------------------------------------
KEY_RULES = {
    "GEMINI_API_KEY": {
        "min_len": 20,
        "max_len": 200,
        "prefixes": None,  # AIza..., AQ...., etc.
        "hint": (
            "Paste the full key from https://aistudio.google.com/apikey. "
            "Usually 20+ characters (AIza, AQ., or similar)."
        ),
    },
    "GROQ_API_KEY": {
        "min_len": 40,
        "max_len": 120,
        "prefixes": ["gsk_"],
        "hint": "Groq keys start with 'gsk_'. Get one at https://console.groq.com/keys",
    },
    "CEREBRAS_API_KEY": {
        "min_len": 20,
        "max_len": 200,
        "prefixes": ["csk-"],  # Cerebras keys often start with csk-
        "hint": (
            "Cerebras keys often start with 'csk-'. "
            "Get one at https://cloud.cerebras.ai"
        ),
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
    # ---------- Groq (free developer tier, needs litellm) ----------
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
    # ---------- Cerebras (free tier, needs litellm) ----------
    "cerebras_llama_3_3_70b": ModelSpec(
        provider="cerebras",
        display_name="Cerebras Llama 3.3 70B",
        model_id="cerebras/llama-3.3-70b",
        secret_key="CEREBRAS_API_KEY",
        tier="Free tier",
        notes="Fast inference on Cerebras free tier. https://cloud.cerebras.ai",
    ),
    "cerebras_llama_3_1_8b": ModelSpec(
        provider="cerebras",
        display_name="Cerebras Llama 3.1 8B",
        model_id="cerebras/llama3.1-8b",
        secret_key="CEREBRAS_API_KEY",
        tier="Free tier",
        notes="Smaller/faster Cerebras free-tier model.",
    ),
}

DEFAULT_MODEL_PRIORITY = [
    "gemini_3_8_flash",
    "gemini_3_5_flash_lite",
    "gemini_2_5_flash",
    "groq_gpt_oss_120b",
    "groq_gpt_oss_20b",
    "groq_qwen_3_8_27b",
    "cerebras_llama_3_3_70b",
    "cerebras_llama_3_1_8b",
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
    if value is None:
        value = get_api_key(secret_key)

    if not value:
        return False, f"{secret_key} is missing. Add it in Streamlit Secrets."

    rules = KEY_RULES.get(secret_key)
    if not rules:
        if len(value) < 10:
            return False, f"{secret_key} looks too short ({len(value)} chars)."
        return True, f"{secret_key} looks present ({len(value)} chars)."

    length = len(value)
    min_len = rules["min_len"]
    max_len = rules["max_len"]
    prefixes = rules.get("prefixes")
    hint = rules.get("hint", "")

    if length < min_len or length > max_len:
        return (
            False,
            f"{secret_key} length looks wrong ({length} chars). "
            f"Expected about {min_len}–{max_len}. {hint}",
        )

    if prefixes:
        if not any(value.startswith(p) for p in prefixes):
            # Soft warning only for Cerebras — prefix can vary by account
            if secret_key == "CEREBRAS_API_KEY":
                return True, (
                    f"{secret_key} format looks OK ({length} chars). "
                    f"(Prefix is not 'csk-' but key is long enough.)"
                )
            expected = " or ".join(f"'{p}'" for p in prefixes)
            return (
                False,
                f"{secret_key} should start with {expected} but starts with "
                f"'{value[: min(12, length)]}...'. {hint}",
            )

    if not re.match(r"^[\x21-\x7E]+$", value):
        return False, f"{secret_key} contains unexpected characters. {hint}"

    return True, f"{secret_key} format looks OK ({length} chars)."


def is_model_available(model_key: str) -> bool:
    if model_key not in MODEL_CATALOG:
        return False
    spec = MODEL_CATALOG[model_key]
    ok, _ = validate_api_key(spec.secret_key)
    return ok


def get_key_status_message(model_key: str) -> str:
    if model_key not in MODEL_CATALOG:
        return "Unknown model."
    spec = MODEL_CATALOG[model_key]
    _, message = validate_api_key(spec.secret_key)
    return message


def available_model_keys():
    return [key for key in MODEL_CATALOG if is_model_available(key)]


def unavailable_model_keys():
    return [key for key in MODEL_CATALOG if not is_model_available(key)]


def default_model_key() -> str:
    for key in DEFAULT_MODEL_PRIORITY:
        if key in MODEL_CATALOG and is_model_available(key):
            return key
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

    return LLM(
        model=spec.crewai_model,
        api_key=api_key,
        temperature=0.2,
    )


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
