import streamlit as st
from model_manager import (
    MODEL_CATALOG,
    configure_agents,
    default_model_key,
    get_key_status_message,
    is_model_available,
    model_label,
    selected_model_info,
    validate_api_key,
)


def render_model_selector(agents):
    st.sidebar.subheader("🤖 AI Model")

    keys = list(MODEL_CATALOG.keys())

    # Default: prefer a model whose key is valid
    preferred = default_model_key()
    current = st.session_state.get("selected_model_key", preferred)
    if current not in keys:
        current = preferred

    # Keep index in range
    try:
        index = keys.index(current)
    except ValueError:
        index = keys.index(preferred) if preferred in keys else 0

    selected = st.sidebar.selectbox(
        "Choose model",
        options=keys,
        index=index,
        format_func=model_label,
        key="model_selector",
        help=(
            "Green = key present and length/format look OK. "
            "Grey = missing or invalid key. "
            "Only free-tier models are listed."
        ),
    )

    st.session_state.selected_model_key = selected
    spec = selected_model_info(selected)

    # Detailed key check for the selected model
    ok, message = validate_api_key(spec.secret_key)

    if not ok:
        st.sidebar.error(f"🔒 {message}")
        st.sidebar.caption(
            f"Fix: add a valid `{spec.secret_key}` in Streamlit Secrets, then reload."
        )
        return False

    st.sidebar.success(f"✅ {message}")
    st.sidebar.caption(
        f"Provider: {spec.provider} • {spec.tier}"
    )

    try:
        configure_agents(agents, selected)
        st.session_state.active_model_key = selected
        return True
    except Exception as exc:
        st.sidebar.error(f"Could not initialize {spec.display_name}: {exc}")
        return False
