"""
Free-tier multi-provider LLM manager for CareerOps AI.
Gemini + Groq + Cerebras only.
"""

import os
import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import litellm
import streamlit as st
from crewai import LLM


# ---------------------------------------------------------------------------
# Message sanitizer
#
# Newer CrewAI / LiteLLM versions can attach a `cache_breakpoint` field to
# messages (used for prompt caching). Gemini tolerates it, but Groq rejects it:
#   "'messages.0' : property 'cache_breakpoint' is unsupported"
# We strip unsupported keys from every message right before the request is sent.
# ---------------------------------------------------------------------------
_UNSUPPORTED_MSG_KEYS = {"cache_breakpoint"}


def _clean_content(content):
    """Strip unsupported keys from structured content blocks (list of dicts)."""
    if isinstance(content, list):
        return [
            {k: v for k, v in block.items() if k not in _UNSUPPORTED_MSG_KEYS}
            if isinstance(block, dict)
            else block
            for block in content
        ]
    return content


def _clean_messages(messages):
    if not isinstance(messages, list):
        return messages
    cleaned = []
    for m in messages:
        if isinstance(m, dict):
            m = {k: v for k, v in m.items() if k not in _UNSUPPORTED_MSG_KEYS}
            if "content" in m:
                m["content"] = _clean_content(m["content"])
        cleaned.append(m)
    return cleaned


def _install_message_sanitizer() -> None:
    # Streamlit reruns this module often; only wrap LiteLLM once.
    if getattr(litellm, "_msg_sanitizer_installed", False):
        return

    _orig_completion = litellm.completion

    def _safe_completion(*args, **kwargs):
        if "messages" in kwargs:
            kwargs["messages"] = _clean_messages(kwargs["messages"])
        return _orig_completion(*args, **kwargs)

    litellm.completion = _safe_completion

    if hasattr(litellm, "acompletion"):
        _orig_acompletion = litellm.acompletion

        async def _safe_acompletion(*args, **kwargs):
            if "messages" in kwargs:
                kwargs["messages"] = _clean_messages(kwargs["messages"])
            return await _orig_acompletion(*args, **kwargs)

        litellm.acompletion = _safe_acompletion

    litellm._msg_sanitizer_installed = True


_install_message_sanitizer()


PLACEHOLDER_VALUES = {
    "", "paste your api key here", "paste_your_api_key_here",
    "your_api_key_here", "your-api-key-here", "changeme",
    "change_me", "null", "none",
}

KEY_RULES = {
    "GEMINI_API_KEY": {
        "min_len": 20, "max_len": 200, "prefixes": None,
        "hint": "From https://aistudio.google.com/apikey (AIza, AQ., etc.).",
    },
    "GROQ_API_KEY": {
        "min_len": 40, "max_len": 120, "prefixes": ["gsk_"],
        "hint": "From https://console.groq.com/keys — starts with gsk_.",
    },
    "CEREBRAS_API_KEY": {
        "min_len": 20, "max_len": 200, "prefixes": ["csk-"],
        "hint": "From https://cloud.cerebras.ai — often starts with csk-.",
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
    "gemini_3_8_flash": ModelSpec(
        "gemini", "Gemini 3.8 Flash", "gemini/gemini-3.8-flash",
        "GEMINI_API_KEY", "Free tier",
    ),
    "gemini_3_5_flash_lite": ModelSpec(
        "gemini", "Gemini 3.5 Flash-Lite", "gemini/gemini-3.5-flash-lite",
        "GEMINI_API_KEY", "Free tier",
    ),
    "gemini_2_5_flash": ModelSpec(
        "gemini", "Gemini 2.5 Flash", "gemini/gemini-2.5-flash",
        "GEMINI_API_KEY", "Free tier",
    ),
    "groq_gpt_oss_120b": ModelSpec(
        "groq", "Groq GPT-OSS 120B", "groq/openai/gpt-oss-120b",
        "GROQ_API_KEY", "Free tier",
    ),
    "groq_gpt_oss_20b": ModelSpec(
        "groq", "Groq GPT-OSS 20B", "groq/openai/gpt-oss-20b",
        "GROQ_API_KEY", "Free tier",
    ),
    "groq_qwen_3_8_27b": ModelSpec(
        "groq", "Groq Qwen3.8 27B", "groq/qwen/qwen3.8-27b",
        "GROQ_API_KEY", "Free tier",
    ),
    "cerebras_llama_3_3_70b": ModelSpec(
        "cerebras", "Cerebras Llama 3.3 70B", "cerebras/llama-3.3-70b",
        "CEREBRAS_API_KEY", "Free tier",
    ),
    "cerebras_llama_3_1_8b": ModelSpec(
        "cerebras", "Cerebras Llama 3.1 8B", "cerebras/llama3.1-8b",
        "CEREBRAS_API_KEY", "Free tier",
    ),
}

DEFAULT_MODEL_PRIORITY = [
    "gemini_3_8_flash", "gemini_3_5_flash_lite", "gemini_2_5_flash",
    "groq_gpt_oss_120b", "groq_gpt_oss_20b", "groq_qwen_3_8_27b",
    "cerebras_llama_3_3_70b", "cerebras_llama_3_1_8b",
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
    if length < rules["min_len"] or length > rules["max_len"]:
        return False, (
            f"{secret_key} length looks wrong ({length} chars). "
            f"Expected about {rules['min_len']}–{rules['max_len']}. {rules['hint']}"
        )

    prefixes = rules.get("prefixes")
    if prefixes and not any(value.startswith(p) for p in prefixes):
        if secret_key == "CEREBRAS_API_KEY":
            return True, f"{secret_key} format looks OK ({length} chars)."
        expected = " or ".join(f"'{p}'" for p in prefixes)
        return False, (
            f"{secret_key} should start with {expected} but starts with "
            f"'{value[:min(12, length)]}...'. {rules['hint']}"
        )

    if not re.match(r"^[\x21-\x7E]+$", value):
        return False, f"{secret_key} contains unexpected characters. {rules['hint']}"

    return True, f"{secret_key} format looks OK ({length} chars)."


def is_model_available(model_key: str) -> bool:
    if model_key not in MODEL_CATALOG:
        return False
    ok, _ = validate_api_key(MODEL_CATALOG[model_key].secret_key)
    return ok


def default_model_key() -> str:
    for key in DEFAULT_MODEL_PRIORITY:
        if key in MODEL_CATALOG and is_model_available(key):
            return key
    return next(iter(MODEL_CATALOG.keys()))


def model_label(model_key: str) -> str:
    spec = MODEL_CATALOG[model_key]
    if is_model_available(model_key):
        return f"🟢 {spec.display_name} • {spec.tier}"
    return f"⚪ {spec.display_name} • API key missing/invalid"


def build_llm(model_key: str) -> LLM:
    if model_key not in MODEL_CATALOG:
        raise ValueError(f"Unknown model: {model_key}")

    spec = MODEL_CATALOG[model_key]
    api_key = get_api_key(spec.secret_key)
    ok, message = validate_api_key(spec.secret_key, api_key)
    if not ok:
        raise ValueError(message)

    return LLM(model=spec.crewai_model, api_key=api_key, temperature=0.2)


def configure_agents(agents: Dict[str, object], model_key: str) -> None:
    llm = build_llm(model_key)
    for agent in agents.values():
        agent.llm = llm


def selected_model_info(model_key: str) -> ModelSpec:
    return MODEL_CATALOG[model_key]
