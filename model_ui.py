import streamlit as st
from model_manager import (
    MODEL_CATALOG,
    build_llm,
    configure_agents,
    is_model_available,
    model_label,
    selected_model_info,
)

def render_model_selector(agents):
    st.sidebar.subheader("🤖 AI Model")

    keys = list(MODEL_CATALOG.keys())

    # Keep the last selection if it is still present.
    current = st.session_state.get("selected_model_key", keys[0])
    if current not in keys:
        current = keys[0]

    def label(key):
        return model_label(key)

    selected = st.sidebar.selectbox(
        "Choose model",
        options=keys,
        index=keys.index(current),
        format_func=label,
        key="model_selector",
        help=(
            "Models with a missing API key are shown with a gray/white "
            "indicator and cannot be used until their key is configured."
        ),
    )

    st.session_state.selected_model_key = selected
    spec = selected_model_info(selected)

    if not is_model_available(selected):
        st.sidebar.warning(
            f"🔒 {spec.secret_key} is missing. "
            f"Add a real key in Streamlit Secrets to enable {spec.display_name}."
        )
        return False

    st.sidebar.success(f"API key ready: {spec.secret_key}")
    st.sidebar.caption(f"Provider: {spec.display_name.split()[0]} • {spec.tier}")

    try:
        configure_agents(agents, selected)
        st.session_state.active_model_key = selected
        return True
    except Exception as exc:
        st.sidebar.error(f"Could not initialize {spec.display_name}: {exc}")
        return False
