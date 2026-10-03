
"""
Gemini-only LLM manager for CareerOps AI.
"""

import os
import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import streamlit as st
from crewai import LLM

PLACEHOLDER_VALUES = {
    "", "paste your api key here", "paste_your_api_key_here",
    "your_api_key_here", "your-api-key-here", "changeme",
    "change_me", "null", "none",
}

KEY_RULES = {
    "GEMINI_API_KEY": {
        "min_len": 20,
        "max_len": 200,
        "prefixes": None,
        "hint": "Get your key from https://aistudio.google.com/apikey",
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
        "gemini",
        "Gemini 3.8 Flash",
        "gemini/gemini-3.8-flash",
        "GEMINI_API_KEY",
        "Free tier",
    ),
    "gemini_3_5_flash_lite": ModelSpec(
        "gemini",
        "Gemini 3.5 Flash-Lite",
        "gemini/gemini-3.5-flash-lite",
        "GEMINI_API_KEY",
        "Free tier",
    ),
    "gemini_2_5_flash": ModelSpec(
        "gemini",
        "Gemini 2.5 Flash",
        "gemini/gemini-2.5-flash",
        "GEMINI_API_KEY",
        "Free tier",
    ),
}

DEFAULT_MODEL_PRIORITY = [
    "gemini_3_8_flash",
    "gemini_3_5_flash_lite",
    "gemini_2_5_flash",
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


def validate_api_key(
    secret_key: str,
    value: Optional[str] = None,
) -> Tuple[bool, str]:

    if value is None:
        value = get_api_key(secret_key)

    if not value:
        return False, (
            f"{secret_key} is missing. "
            "Add it in Streamlit Secrets."
        )

    rules = KEY_RULES.get(secret_key)

    if not rules:
        if len(value) < 10:
            return False, (
                f"{secret_key} looks too short "
                f"({len(value)} chars)."
            )
        return True, (
            f"{secret_key} looks present "
            f"({len(value)} chars)."
        )

    length = len(value)

    if length < rules["min_len"] or length > rules["max_len"]:
        return False, (
            f"{secret_key} length looks wrong "
            f"({length} chars). "
            f"Expected about {rules['min_len']}–"
            f"{rules['max_len']}. {rules['hint']}"
        )

    prefixes = rules.get("prefixes")

    if prefixes and not any(
        value.startswith(p) for p in prefixes
    ):
        expected = " or ".join(
            f"'{p}'" for p in prefixes
        )
        return False, (
            f"{secret_key} should start with {expected}. "
            f"{rules['hint']}"
        )

    if not re.match(r"^[\x21-\x7E]+$", value):
        return False, (
            f"{secret_key} contains unexpected characters. "
            f"{rules['hint']}"
        )

    return True, (
        f"{secret_key} format looks OK ({length} chars)."
    )


def is_model_available(model_key: str) -> bool:
    if model_key not in MODEL_CATALOG:
        return False

    ok, _ = validate_api_key(
        MODEL_CATALOG[model_key].secret_key
    )

    return ok


def default_model_key() -> str:
    for key in DEFAULT_MODEL_PRIORITY:
        if is_model_available(key):
            return key

    return DEFAULT_MODEL_PRIORITY[0]


def model_label(model_key: str) -> str:
    spec = MODEL_CATALOG[model_key]

    if is_model_available(model_key):
        return f"🟢 {spec.display_name} • {spec.tier}"

    return (
        f"⚪ {spec.display_name} • "
        "API key missing/invalid"
    )


def build_llm(model_key: str) -> LLM:
    if model_key not in MODEL_CATALOG:
        raise ValueError(f"Unknown model: {model_key}")

    spec = MODEL_CATALOG[model_key]
    api_key = get_api_key(spec.secret_key)

    ok, message = validate_api_key(
        spec.secret_key,
        api_key,
    )

    if not ok:
        raise ValueError(message)

    return LLM(
        model=spec.crewai_model,
        api_key=api_key,
        temperature=0.2,
    )


def configure_agents(
    agents: Dict[str, object],
    model_key: str,
) -> None:
    llm = build_llm(model_key)

    for agent in agents.values():
        agent.llm = llm


def selected_model_info(model_key: str) -> ModelSpec:
    return MODEL_CATALOG[model_key]
