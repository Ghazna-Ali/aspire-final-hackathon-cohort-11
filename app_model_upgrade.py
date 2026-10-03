from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

# 1. Add the model UI import.
old_import = "from memory import CareerMemory\n"
new_import = old_import + "from model_ui import render_model_selector\n"
if new_import not in text:
    if old_import not in text:
        raise SystemExit("Could not find the expected import section in app.py")
    text = text.replace(old_import, new_import, 1)

# 2. Configure the selected LLM after the feature agents are merged.
old_registry = """AGENTS.update(FEATURE_AGENTS)
AGENT_DESCRIPTIONS.update(FEATURE_DESCRIPTIONS)
TASKS.update(FEATURE_TASKS)
"""
new_registry = old_registry + """
# ============================================================
# AI MODEL CONFIGURATION
# ============================================================
# All existing agents use the model selected in the sidebar.
# Models without a configured API key remain visible but cannot run.
MODEL_READY = render_model_selector(AGENTS)
"""
if new_registry not in text:
    if old_registry not in text:
        raise SystemExit("Could not find the AGENTS/TASKS registry section in app.py")
    text = text.replace(old_registry, new_registry, 1)

# 3. Prevent execution when the selected model has no key.
old_run = """if run_button:

    validation_errors = validate_inputs()
"""
new_run = """if run_button:

    if not MODEL_READY:
        st.error(
            "The selected AI model is not available. "
            "Configure its API key in Streamlit Secrets first."
        )
        st.stop()

    validation_errors = validate_inputs()
"""
if new_run not in text:
    if old_run not in text:
        raise SystemExit("Could not find the Run button section in app.py")
    text = text.replace(old_run, new_run, 1)

# 4. Make the old Gemini-only status block generic.
start = """    try:
        secret_key_exists = bool(
            st.secrets.get("GEMINI_API_KEY")
        )
    except Exception:
        secret_key_exists = False

    environment_key_exists = bool(
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )

    gemini_key_exists = (
        secret_key_exists or environment_key_exists
    )
    if gemini_key_exists:
        st.success("Gemini API key detected")
    else:
        st.error("Gemini API key not detected")
"""
replacement = """    # Provider/model availability is shown above in the AI Model section.
    # Keep this area focused on application-level status.
    st.success("Multi-provider AI configuration loaded")
"""
if replacement not in text:
    if start in text:
        text = text.replace(start, replacement, 1)

# 5. Make quota error text provider-neutral.
text = text.replace(
    'st.error(\n        "Gemini API quota has been exhausted."\n    )',
    'st.error(\n        "The selected AI provider has reported a quota or usage limit."\n    )',
    1,
)
text = text.replace(
    """        Gemini project has reached its current API quota.

        This is different from a temporary API error, so the app
        will **not keep retrying automatically**.

        You can:
        - Wait for the quota to reset
        - Check your Gemini API usage
        - Use a different Gemini project/API key
        - Upgrade the applicable Gemini API plan
""",
    """        The selected provider/model has reached a quota or usage limit.

        This is different from a temporary API error, so the app
        will **not keep retrying automatically**.

        You can:
        - Wait for the provider quota to reset
        - Check the provider's API usage
        - Select another configured model
        - Add another provider API key in Streamlit Secrets
""",
    1,
)

APP.write_text(text, encoding="utf-8")
print("Patched app.py successfully.")
