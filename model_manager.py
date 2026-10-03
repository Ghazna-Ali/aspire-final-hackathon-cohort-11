"""
Free-tier multi-provider LLM manager for CareerOps AI (Oct 2026).

Only models with a documented no-card free tier are listed.
API keys are read from Streamlit secrets first, then environment variables.
Never put real API keys in this file.
"""
import os
from dataclasses import dataclass
from typing import Dict, Optional

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


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    display_name: str
    model_id: str          # string passed to crewai.LLM(model=...)
    secret_key: str
    tier: str
    notes: str = ""

    @property
    def crewai_model(self) -> str:
        return self.model_id


# ------------------------------------------------------------
# FREE-TIER ONLY CATALOG (October 2026)
# ------------------------------------------------------------
MODEL_CATALOG: Dict[str, ModelSpec] = {
    # ---------- Google Gemini (native, free tier) ----------
    "gemini_3_8_flash": ModelSpec(
        provider="gemini",
        display_name="Gemini 3.8 Flash",
        model_id="gemini/gemini-3.8-flash",
        secret_key="GEMINI_API_KEY",
        tier="Free tier",
        notes="Google AI Studio free tier. ~15 RPM, generous daily quota. Native CrewAI.",
    ),
    "gemini_3_5_flash_lite": ModelSpec(
        provider="gemini",
        display_name="Gemini 3.5 Flash-Lite",
        model_id="gemini/gemini-3.5-flash-lite",
        secret_key="GEMINI_API_KEY",
        tier="Free tier",
        notes="Cheapest/fastest Gemini free-tier model. Native CrewAI.",
    ),
    "gemini_2_5_flash": ModelSpec(
        provider="gemini",
        display_name="Gemini 2.5 Flash",
        model_id="gemini/gemini-2.5-flash",
        secret_key="GEMINI_API_KEY",
        tier="Free tier",
        notes="Still on free tier for many projects. Native CrewAI.",
    ),

    # ---------- Groq (free developer tier, needs litellm) ----------
    "groq_gpt_oss_120b": ModelSpec(
        provider="groq",
        display_name="Groq GPT-OSS 120B",
        model_id="groq/openai/gpt-oss-120b",
        secret_key="GROQ_API_KEY",
        tier="Free tier",
        notes="Very fast. ~30 RPM / 1k RPD / 200k tokens/day on free plan.",
    ),
    "groq_gpt_oss_20b": ModelSpec(
        provider="groq",
        display_name="Groq GPT-OSS 20B",
        model_id="groq/openai/gpt-oss-20b",
        secret_key="GROQ_API_KEY",
        tier="Free tier",
        notes="Faster & lighter than 120B. Same free rate limits.",
    ),
    "groq_qwen_3_8_27b": ModelSpec(
        provider="groq",
        display_name="Groq Qwen3.8 27B",
        model_id="groq/qwen/qwen3.8-27b",
        secret_key="GROQ_API_KEY",
        tier="Free tier",
        notes="Strong open model on Groq free tier.",
    ),

    # ---------- OpenRouter free models (needs litellm) ----------
    "openrouter_qwen_3_8_27b": ModelSpec(
        provider="openrouter",
        display_name="OpenRouter Qwen3.8 27B (free)",
        model_id="openrouter/qwen/qwen3.8-27b:free",
        secret_key="OPENROUTER_API_KEY",
        tier="Free tier",
        notes=":free route. ~20 RPM / 50 RPD (1k RPD after $10 lifetime credit).",
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
        notes="NVIDIA open MoE model, free route on OpenRouter.",
    ),

    # ---------- Mistral free Experiment plan (needs litellm) ----------
    "mistral_small": ModelSpec(
        provider="mistral",
        display_name="Mistral Small (free)",
        model_id="mistral/mistral-small-latest",
        secret_key="MISTRAL_API_KEY",
        tier="Free Experiment",
        notes="Mistral La Plateforme free Experiment plan. Rate-limited.",
    ),
}


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


def provider_keys() -> Dict[str, Optional[str]]:
    return {
        "GEMINI_API_KEY": get_api_key("GEMINI_API_KEY"),
        "GROQ_API_KEY": get_api_key("GROQ_API_KEY"),
        "OPENROUTER_API_KEY": get_api_key("OPENROUTER_API_KEY"),
        "MISTRAL_API_KEY": get_api_key("MISTRAL_API_KEY"),
    }


def is_model_available(model_key: str) -> bool:
    spec = MODEL_CATALOG[model_key]
    return bool(get_api_key(spec.secret_key))


def available_model_keys():
    return [key for key in MODEL_CATALOG if is_model_available(key)]


def unavailable_model_keys():
    return [key for key in MODEL_CATALOG if not is_model_available(key)]


def model_label(model_key: str) -> str:
    spec = MODEL_CATALOG[model_key]
    if is_model_available(model_key):
        return f"🟢 {spec.display_name}  •  {spec.tier}"
    return f"⚪ {spec.display_name}  •  API key missing"


def build_llm(model_key: str) -> LLM:
    if model_key not in MODEL_CATALOG:
        raise ValueError(f"Unknown model: {model_key}")

    spec = MODEL_CATALOG[model_key]
    api_key = get_api_key(spec.secret_key)

    if not api_key:
        raise ValueError(
            f"{spec.secret_key} is not configured. "
            f"Add a real API key in Streamlit Secrets before selecting {spec.display_name}."
        )

    # OpenRouter needs base_url for reliability with CrewAI + LiteLLM
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
        configured = is_model_available(key)
        rows.append(
            {
                "model_key": key,
                "provider": spec.provider,
                "model": spec.display_name,
                "tier": spec.tier,
                "configured": configured,
                "secret": spec.secret_key,
            }
        )
    return rows


def configure_agents(agents: Dict[str, object], model_key: str) -> None:
    """Assign the selected CrewAI LLM to every existing agent."""
    llm = build_llm(model_key)
    for agent in agents.values():
        agent.llm = llm


def selected_model_info(model_key: str) -> ModelSpec:
    return MODEL_CATALOG[model_key]
