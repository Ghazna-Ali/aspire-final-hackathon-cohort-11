import streamlit as st
from model_manager import (
    MODEL_CATALOG,
    configure_agents,
    default_model_key,
    model_label,
    selected_model_info,
    validate_api_key,
)


def render_model_selector(agents, container=None):
    """
    Render model picker into `container` (column) or sidebar if None.
    Returns True when the selected model is ready to run.
    """
    ui = container if container is not None else st.sidebar

    ui.markdown("##### Model")

    keys = list(MODEL_CATALOG.keys())
    preferred = default_model_key()
    current = st.session_state.get("selected_model_key", preferred)
    if current not in keys:
        current = preferred

    try:
        index = keys.index(current)
    except ValueError:
        index = 0

    selected = ui.selectbox(
        "Model",
        options=keys,
        index=index,
        format_func=model_label,
        key="model_selector",
        label_visibility="collapsed",
        help="Green = key OK. Grey = missing or invalid key.",
    )

    st.session_state.selected_model_key = selected
    spec = selected_model_info(selected)
    ok, message = validate_api_key(spec.secret_key)

    if not ok:
        ui.error(message)
        ui.caption(f"Add `{spec.secret_key}` in Streamlit Secrets.")
        return False

    ui.success(message)
    ui.caption(f"{spec.provider} · {spec.tier}")

    try:
        configure_agents(agents, selected)
        st.session_state.active_model_key = selected
        return True
    except Exception as exc:
        ui.error(f"Could not initialize {spec.display_name}: {exc}")
        return False
