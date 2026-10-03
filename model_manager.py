"""
Multi-provider LLM manager for CareerOps AI.

Supported providers:
- Google Gemini
- OpenAI GPT
- Anthropic Claude
- xAI Grok

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
    model_id: str
    secret_key: str
    tier: str
    notes: str = ""

    @property
    def crewai_model(self) -> str:
        return f"{self.provider}/{self.model_id}"


# Keep model definitions in one place so they can be updated without
# changing any agent code. "free" means the provider documents a free
# API tier for that model/provider; it does NOT mean unlimited usage.
MODEL_CATALOG: Dict[str, ModelSpec] = {
    # Google currently documents a Gemini API free tier for selected models.
    # Keep this entry easy to update as Google changes the catalog.
    "gemini_3_5_flash": ModelSpec(
        provider="gemini",
        display_name="Gemini 3.8 Flash",
        model_id="gemini-3.8-flash",
        secret_key="GEMINI_API_KEY",
        tier="Free tier",
        notes="Google Gemini API free-tier model (subject to rate limits).",
    ),
    "gemini_3_flash": ModelSpec(
        provider="gemini",
        display_name="Gemini 3 Flash",
        model_id="gemini-3-flash",
        secret_key="GEMINI_API_KEY",
        tier="Free tier / availability varies",
        notes="Check the current Gemini API model catalog before deployment.",
    ),

    # OpenAI API access generally requires API billing/credits.
    "gpt_6_luna": ModelSpec(
        provider="openai",
        display_name="GPT-6 Luna",
        model_id="gpt-6-luna",
        secret_key="OPENAI_API_KEY",
        tier="Paid API",
        notes="OpenAI API model; billing/credits may be required.",
    ),
    "gpt_6_1_sol": ModelSpec(
        provider="openai",
        display_name="GPT-6.1 Sol",
        model_id="gpt-6.1-sol",
        secret_key="OPENAI_API_KEY",
        tier="Paid API",
        notes="OpenAI API model; billing/credits may be required.",
    ),

    # Anthropic API access generally requires API credits.
    "claude_sonnet_5": ModelSpec(
        provider="anthropic",
        display_name="Claude Sonnet 5",
        model_id="claude-sonnet-5",
        secret_key="ANTHROPIC_API_KEY",
        tier="Paid API",
        notes="Anthropic API model; billing/credits may be required.",
    ),
    "claude_opus_5_5": ModelSpec(
        provider="anthropic",
        display_name="Claude Opus 5.5",
        model_id="claude-opus-5.5",
        secret_key="ANTHROPIC_API_KEY",
        tier="Paid API",
        notes="Anthropic API model; billing/credits may be required.",
    ),

    # xAI API access generally requires API credits.
    "grok_4_6": ModelSpec(
        provider="xai",
        display_name="Grok 4.6",
        model_id="grok-4.6",
        secret_key="XAI_API_KEY",
        tier="Paid API",
        notes="xAI API model; billing/credits may be required.",
    ),
    "grok_4_5": ModelSpec(
        provider="xai",
        display_name="Grok 4.5",
        model_id="grok-4.5",
        secret_key="XAI_API_KEY",
        tier="Paid API",
        notes="xAI API model; billing/credits may be required.",
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
        "OPENAI_API_KEY": get_api_key("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": get_api_key("ANTHROPIC_API_KEY"),
        "XAI_API_KEY": get_api_key("XAI_API_KEY"),
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

    return LLM(
        model=spec.crewai_model,
        api_key=api_key,
        temperature=0.2,
    )


def get_model_status_rows():
    rows = []
    for key, spec in MODEL_CATALOG.items():
        configured = is_model_available(key)
        rows.append(
            {
                "model_key": key,
                "provider": spec.display_name.split()[0],
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
