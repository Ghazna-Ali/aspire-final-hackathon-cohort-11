
import os
import re
import time
import tempfile
import uuid
from datetime import datetime


# ============================================================
# IMPORTS
# ============================================================

import streamlit as st
from crewai import Crew, Process

from agents import (
    manager_agent,
    job_analyst_agent,
    cv_agent,
    research_agent,
    application_agent,
    interview_agent,
    critic_agent,
)

from tasks import TASKS
from tools import extract_cv_text
from memory import CareerMemory
from model_ui import render_model_selector
from report import build_pdf

from features import (
    FEATURE_AGENTS,
    FEATURE_TASKS,
    FEATURE_DESCRIPTIONS,
    parse_match_score,
)

from model_manager import (
    is_model_available,
    default_model_key,
    configure_agents,
)


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="CareerOps AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    header[data-testid="stHeader"] {
        background: transparent;
    }

    div[data-testid="stToolbar"] {
        display: none;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    .stApp {
        background: #0b1220;
    }

    .block-container {
        padding-top: 0.85rem;
        padding-bottom: 1.5rem;
        max-width: 1400px;
    }

    .stApp,
    .stMarkdown,
    .stMarkdown p,
    label {
        color: #e2e8f0;
    }

    div[data-testid="stCaptionContainer"],
    div[data-testid="stCaptionContainer"] p {
        color: #94a3b8 !important;
    }

    .co-scroll {
        max-height: calc(100vh - 5rem);
        overflow-y: auto;
        overflow-x: hidden;
        padding-right: 0.3rem;
        scrollbar-width: thin;
        scrollbar-color: #475569 transparent;
    }

    .co-scroll::-webkit-scrollbar {
        width: 6px;
    }

    .co-scroll::-webkit-scrollbar-thumb {
        background: #475569;
        border-radius: 999px;
    }

    .co-hero {
        background: linear-gradient(
            135deg,
            #0f172a 0%,
            #1e293b 40%,
            #312e81 100%
        );

        border: 1px solid rgba(129, 140, 248, 0.35);
        border-radius: 16px;
        padding: 1.35rem 1.5rem 1.2rem 1.5rem;
        margin-bottom: 0.75rem;

        box-shadow:
            0 10px 40px rgba(0, 0, 0, 0.35),
            0 0 0 1px rgba(129, 140, 248, 0.08);
    }

    .co-kicker {
        font-size: 0.72rem;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: #a5b4fc;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }

    .co-hero-title {
        font-size: 1.65rem;
        font-weight: 800;
        color: #f8fafc;
        margin: 0;
        letter-spacing: -0.03em;
        line-height: 1.2;
    }

    .co-hero-sub {
        color: #cbd5e1;
        font-size: 0.92rem;
        margin: 0.45rem 0 0 0;
        line-height: 1.5;
        max-width: 40rem;
    }

    .co-hero-sub strong {
        color: #e0e7ff;
        font-weight: 600;
    }

    .co-section-label {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #94a3b8;
        margin: 0.3rem 0 0.3rem 0;
    }

    .co-muted {
        color: #94a3b8;
        font-size: 0.82rem;
    }

    .co-agent-pill {
        display: inline-block;
        background: #312e81;
        color: #e0e7ff;
        border-radius: 999px;
        padding: 0.25rem 0.75rem;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 0.35rem 0 0.5rem 0;
        border: 1px solid rgba(165, 180, 252, 0.35);
    }

    .co-field-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #e2e8f0;
        margin-bottom: 0.2rem;
    }

    div[data-testid="column"] div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.8rem;
        padding-top: 0.35rem;
        padding-bottom: 0.35rem;
        min-height: 2.1rem;
        border: 1px solid #334155;
        background: #1e293b;
        color: #f1f5f9;
    }

    div[data-testid="column"] div.stButton > button:hover {
        border-color: #818cf8;
    }

    div.stButton > button[kind="primary"] {
        background: #4f46e5;
        color: #ffffff;
        border: 1px solid #6366f1;
    }

    div.stButton > button[kind="primary"]:hover {
        background: #4338ca;
        border-color: #4338ca;
    }

    div[data-baseweb="select"] > div,
    .stTextArea textarea,
    .stTextInput input {
        background-color: #0f172a !important;
        color: #e2e8f0 !important;
        border-color: #334155 !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# REGISTRIES
# ============================================================

AGENTS = {
    "Manager": manager_agent,
    "Job Analyst": job_analyst_agent,
    "CV Analyst": cv_agent,
    "Research Agent": research_agent,
    "Application Agent": application_agent,
    "Interview Agent": interview_agent,
    "Critic Agent": critic_agent,
}

AGENT_DESCRIPTIONS = {
    "Manager": "Structured overview: strengths, gaps, next steps.",
    "Job Analyst": "Break down requirements, skills, and keywords.",
    "CV Analyst": "CV vs job: matches, gaps, improvements.",
    "Research Agent": "Company and opportunity signals from your text.",
    "Application Agent": "Summaries, CV tweaks, cover-letter content.",
    "Interview Agent": "Technical, behavioral, and situational prep.",
    "Critic Agent": "Weaknesses and missing evidence in your materials.",
}

AGENTS.update(FEATURE_AGENTS)
AGENT_DESCRIPTIONS.update(FEATURE_DESCRIPTIONS)
TASKS.update(FEATURE_TASKS)


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "cv_text": "",
    "job_description": "",
    "career_request": "",
    "selected_agent": "Job Analyst",
    "result": "",
    "result_agent": "",
    "last_run_time": None,
    "insight_archive": [],
    "active_insight_id": None,
    "briefing_open": False,
    "chat_messages": [],
    "left_open": True,
    "right_open": True,
    "left_width": 1.2,
    "right_width": 1.2,
    "run_status": "idle",
    "run_error": "",
    "run_started_at": None,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ============================================================
# RESET / STATE HELPERS
# ============================================================

def reset_everything():
    st.session_state.cv_text = ""
    st.session_state.job_description = ""
    st.session_state.career_request = ""
    st.session_state.selected_agent = "Job Analyst"
    st.session_state.result = ""
    st.session_state.result_agent = ""
    st.session_state.last_run_time = None
    st.session_state.insight_archive = []
    st.session_state.active_insight_id = None
    st.session_state.chat_messages = []
    st.session_state.run_status = "idle"
    st.session_state.run_error = ""
    st.session_state.run_started_at = None


def clear_run_state():
    st.session_state.run_status = "idle"
    st.session_state.run_error = ""
    st.session_state.run_started_at = None


def archive_insight(agent_name, text, career_request=""):
    item = {
        "id": str(uuid.uuid4()),
        "agent": agent_name,
        "text": text,
        "career_request": career_request,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    st.session_state.insight_archive.insert(0, item)

    st.session_state.insight_archive = (
        st.session_state.insight_archive[:30]
    )

    st.session_state.active_insight_id = item["id"]

    return item


def get_active_insight():
    aid = st.session_state.active_insight_id

    if not aid:
        return None

    for item in st.session_state.insight_archive:
        if item["id"] == aid:
            return item

    return None


# ============================================================
# ERROR HELPERS
# ============================================================

def is_daily_quota_error(error):
    message = str(error).upper()

    patterns = [
        "GENERATEREQUESTSPERDAYPERPROJECTPERMODEL-FREETIER",
        "EXCEEDED YOUR CURRENT QUOTA",
        "QUOTA EXCEEDED",
        "QUOTA_EXCEEDED",
        "PERDAYPERPROJECTPERMODEL",
        "RATE LIMIT",
        "RATE_LIMIT_EXCEEDED",
        "INSUFFICIENT_QUOTA",
    ]

    return any(
        pattern in message
        for pattern in patterns
    )


def is_retryable_ai_error(error):
    if is_daily_quota_error(error):
        return False

    message = str(error).upper()

    patterns = [
        "503",
        "SERVICE_UNAVAILABLE",
        "UNAVAILABLE",
        "429",
        "RESOURCE_EXHAUSTED",
        "RATE_LIMIT",
        "TOO MANY REQUESTS",
        "500",
        "502",
        "504",
        "INTERNAL SERVER ERROR",
        "BAD GATEWAY",
        "GATEWAY TIMEOUT",
    ]

    return any(
        pattern in message
        for pattern in patterns
    )


# ============================================================
# CREW RETRY
# ============================================================

def kickoff_with_retry(
    crew,
    inputs,
    max_attempts=4,
):
    delays = [5, 15, 30]

    for attempt in range(max_attempts):

        try:
            return crew.kickoff(
                inputs=inputs
            )

        except Exception as error:

            if is_daily_quota_error(error):
                raise error

            if not is_retryable_ai_error(error):
                raise error

            if attempt == max_attempts - 1:
                raise error

            delay = delays[
                min(
                    attempt,
                    len(delays) - 1,
                )
            ]

            st.warning(
                f"Temporary API issue "
                f"(attempt {attempt + 1}/{max_attempts}). "
                f"Retrying in {delay}s…"
            )

            time.sleep(delay)


# ============================================================
# CREW CREATION
# ============================================================

def create_single_agent_crew(agent_name):

    if agent_name not in AGENTS:
        raise ValueError(
            f"Unknown agent: {agent_name}"
        )

    if agent_name not in TASKS:
        raise ValueError(
            f"No task configured for: {agent_name}"
        )

    return Crew(
        agents=[AGENTS[agent_name]],
        tasks=[TASKS[agent_name]],
        process=Process.sequential,
        verbose=True,
    )


# ============================================================
# RUN SELECTED AGENT
# ============================================================

def run_selected_agent(
    agent_name,
    cv_text,
    job_description,
    career_request,
):

    crew = create_single_agent_crew(
        agent_name
    )

    inputs = {
        "cv_text": cv_text or "(not provided)",
        "job_description": (
            job_description
            or "(not provided)"
        ),
        "career_request": (
            career_request
            or "Produce the standard analysis for this agent."
        ),
    }

    try:

        memory = CareerMemory()

        if hasattr(memory, "set_cv"):
            memory.set_cv(cv_text)

        if hasattr(memory, "set_job_description"):
            memory.set_job_description(
                job_description
            )

        if hasattr(memory, "set_career_request"):
            memory.set_career_request(
                career_request
            )

    except Exception:
        pass

    return kickoff_with_retry(
        crew,
        inputs,
    )


# ============================================================
# RESULT EXTRACTION
# ============================================================

def extract_result_text(result):

    if result is None:
        return ""

    if (
        hasattr(result, "raw")
        and result.raw is not None
    ):
        return str(result.raw)

    return str(result)


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_inputs():

    errors = []

    if not st.session_state.cv_text.strip():
        errors.append(
            "Add your CV (upload or paste)."
        )

    if not st.session_state.job_description.strip():
        errors.append(
            "Add the job description."
        )

    return errors


# ============================================================
# RESULT RENDERING
# ============================================================

def render_modular_result(
    agent_name,
    text,
):

    if not text:
        st.info("No content.")
        return

    if agent_name == "Job Match Score":

        match = parse_match_score(text)

        if match:

            c1, c2 = st.columns(
                [1, 2]
            )

            with c1:

                st.metric(
                    "Match",
                    f"{match['overall']}%",
                )

                st.progress(
                    match["overall"] / 100.0
                )

            with c2:

                if match.get("breakdown"):

                    cols = st.columns(
                        len(
                            match["breakdown"]
                        )
                    )

                    for col, (
                        category,
                        value,
                    ) in zip(
                        cols,
                        match["breakdown"].items(),
                    ):

                        col.metric(
                            category.split()[0],
                            f"{value}",
                        )

    if agent_name == "Job Legitimacy Check":

        match = re.search(
            r"Legitimacy Score:\s*(\d{1,3})",
            text,
            re.I,
        )

        if match:

            score = min(
                100,
                max(
                    0,
                    int(match.group(1)),
                ),
            )

            st.metric(
                "Legitimacy score",
                f"{score}/100",
            )

            st.progress(
                score / 100.0
            )

    sections = re.split(
        r"(?m)^##\s+",
        text,
    )

    if len(sections) > 1:

        st.markdown(
            '<div class="co-section-label">Modules</div>',
            unsafe_allow_html=True,
        )

        for block in sections[1:]:

            lines = block.strip().split(
                "\n",
                1,
            )

            title = lines[0].strip()

            body = (
                lines[1].strip()
                if len(lines) > 1
                else ""
            )

            with st.expander(
                title,
                expanded=False,
            ):

                st.markdown(
                    body
                    if body
                    else "_No detail._"
                )

        with st.expander(
            "Full report",
            expanded=False,
        ):

            st.markdown(text)

    else:

        with st.expander(
            "Full report",
            expanded=True,
        ):

            st.markdown(text)


# ============================================================
# STALE RUN DETECTION
# ============================================================

if (
    st.session_state.run_status == "running"
    and st.session_state.run_started_at
):

    try:

        started = datetime.strptime(
            st.session_state.run_started_at,
            "%Y-%m-%d %H:%M:%S",
        )

        if (
            datetime.now() - started
        ).total_seconds() > 600:

            st.session_state.run_status = (
                "error"
            )

            st.session_state.run_error = (
                "Previous run did not finish "
                "(timeout or disconnect). "
                "You can run again."
            )

            st.session_state.run_started_at = None

    except Exception:
        clear_run_state()


# ============================================================
# LAYOUT
# ============================================================

left_open = st.session_state.left_open
right_open = st.session_state.right_open

left_w = float(
    st.session_state.get(
        "left_width",
        1.2,
    )
)

right_w = float(
    st.session_state.get(
        "right_width",
        1.2,
    )
)

widths = []

if left_open:
    widths.append(left_w)

widths.append(2.6)

if right_open:
    widths.append(right_w)

cols = st.columns(
    widths,
    gap="medium",
)

idx = 0

left_panel = None

if left_open:

    left_panel = cols[idx]
    idx += 1

center = cols[idx]
idx += 1

right_panel = None

if right_open:
    right_panel = cols[idx]


MODEL_READY = False

selected_agent = (
    st.session_state.selected_agent
)

run_busy = (
    st.session_state.run_status == "running"
)


# ============================================================
# SETTINGS
# ============================================================

if left_panel is not None:

    with left_panel:

        st.markdown(
            '<div class="co-scroll">',
            unsafe_allow_html=True,
        )

        h1, h2 = st.columns(
            [5, 1]
        )

        with h1:
            st.markdown(
                "### Settings"
            )

        with h2:

            if st.button(
                "×",
                key="close_left",
                help="Hide Settings",
            ):

                st.session_state.left_open = False
                st.rerun()

        st.markdown(
            '<div class="co-field-label">Panel width</div>',
            unsafe_allow_html=True,
        )

        new_left_w = st.slider(
            "Left panel width",
            min_value=0.8,
            max_value=2.5,
            value=float(
                st.session_state.left_width
            ),
            step=0.05,
            key="left_width_slider",
            label_visibility="collapsed",
        )

        if (
            new_left_w
            != st.session_state.left_width
        ):

            st.session_state.left_width = (
                new_left_w
            )

            st.rerun()

        MODEL_READY = render_model_selector(
            AGENTS,
            container=left_panel,
        )

        st.markdown(
            '<div class="co-section-label">Status</div>',
            unsafe_allow_html=True,
        )

        if MODEL_READY:
            st.success(
                "Model ready"
            )
        else:
            st.warning(
                "Configure an API key"
            )

        st.caption(
            "One agent per run. "
            "Results go to Insight Archive."
        )

        st.markdown("---")

        if st.button(
            "Reset workspace",
            use_container_width=True,
            key="reset_ws",
        ):

            reset_everything()
            st.rerun()

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

else:

    key = st.session_state.get(
        "selected_model_key",
        default_model_key(),
    )

    MODEL_READY = is_model_available(
        key
    )

    if MODEL_READY:

        try:

            configure_agents(
                AGENTS,
                key,
            )

        except Exception:

            MODEL_READY = False


# ============================================================
# ANALYSIS PANEL
# ============================================================

if right_panel is not None:

    with right_panel:

        st.markdown(
            '<div class="co-scroll">',
            unsafe_allow_html=True,
        )

        h1, h2 = st.columns(
            [5, 1]
        )

        with h1:
            st.markdown(
                "### Analysis"
            )

        with h2:

            if st.button(
                "×",
                key="close_right",
                help="Hide Analysis",
            ):

                st.session_state.right_open = False
                st.rerun()

        st.markdown(
            '<div class="co-field-label">Panel width</div>',
            unsafe_allow_html=True,
        )

        new_right_w = st.slider(
            "Right panel width",
            min_value=0.8,
            max_value=2.5,
            value=float(
                st.session_state.right_width
            ),
            step=0.05,
            key="right_width_slider",
            label_visibility="collapsed",
        )

        if (
            new_right_w
            != st.session_state.right_width
        ):

            st.session_state.right_width = (
                new_right_w
            )

            st.rerun()

        st.markdown(
            '<div class="co-field-label">Analysis type</div>',
            unsafe_allow_html=True,
        )

        agent_names = list(
            AGENTS.keys()
        )

        try:

            a_index = agent_names.index(
                st.session_state.selected_agent
            )

        except ValueError:

            a_index = 0

        selected_agent = st.selectbox(
            "Analysis type",
            options=agent_names,
            index=a_index,
            label_visibility="collapsed",
            key="agent_select_box",
            disabled=run_busy,
            help="Choose before running.",
        )

        if not run_busy:
            st.session_state.selected_agent = (
                selected_agent
            )

        selected_agent = (
            st.session_state.selected_agent
        )

        st.caption(
            AGENT_DESCRIPTIONS.get(
                selected_agent,
                "",
            )
        )

        st.markdown(
            '<div class="co-section-label">Insight Archive</div>',
            unsafe_allow_html=True,
        )

        st.caption(
            "Previous outputs are kept "
            "when you switch agents."
        )

        if not st.session_state.insight_archive:

            st.markdown(
                '<p class="co-muted">'
                "No saved insights yet."
                "</p>",
                unsafe_allow_html=True,
            )

        else:

            for item in (
                st.session_state.insight_archive[:12]
            ):

                label = (
                    f"{item['agent']} · "
                    f"{item['time']}"
                )

                if st.button(
                    label,
                    key=f"arch_{item['id']}",
                    use_container_width=True,
                ):

                    st.session_state.active_insight_id = (
                        item["id"]
                    )

                    st.session_state.result = (
                        item["text"]
                    )

                    st.session_state.result_agent = (
                        item["agent"]
                    )

                    st.session_state.last_run_time = (
                        item["time"]
                    )

                    st.rerun()

        st.markdown("---")

        st.markdown(
            '<div class="co-section-label">'
            "Context briefing"
            "</div>",
            unsafe_allow_html=True,
        )

        st.caption(
            "Optional. Not required to run."
        )

        briefing_open = st.toggle(
            "Show briefing fields",
            value=st.session_state.briefing_open,
            key="briefing_toggle",
        )

        st.session_state.briefing_open = (
            briefing_open
        )

        if briefing_open:

            st.markdown(
                '<div class="co-field-label">'
                "Extra instructions"
                "</div>",
                unsafe_allow_html=True,
            )

            st.caption(
                "Optional — only used if "
                "you fill this in."
            )

            briefing_text = st.text_area(
                "Extra instructions",
                value=(
                    st.session_state.career_request
                ),
                key="career_request_box",
                height=110,
                placeholder=(
                    "Example: Focus on remote roles "
                    "in Europe. Keep answers concise."
                ),
                label_visibility="collapsed",
            )

            st.session_state.career_request = (
                briefing_text
            )

            if st.session_state.insight_archive:

                st.markdown(
                    '<div class="co-field-label">'
                    "Recent insights"
                    "</div>",
                    unsafe_allow_html=True,
                )

                for item in (
                    st.session_state.insight_archive[:3]
                ):

                    st.markdown(
                        f"- **{item['agent']}** "
                        f"({item['time']})"
                    )

            user_note = st.chat_input(
                "Add a short note for this run"
            )

            if user_note:

                st.session_state.chat_messages.append(
                    {
                        "role": "user",
                        "content": user_note,
                    }
                )

                st.session_state.career_request = (
                    (
                        st.session_state.career_request
                        + "\n"
                        + user_note
                    ).strip()
                )

                st.rerun()

            for msg in (
                st.session_state.chat_messages[-6:]
            ):

                with st.chat_message(
                    msg["role"]
                ):

                    st.write(
                        msg["content"]
                    )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

else:

    selected_agent = (
        st.session_state.selected_agent
    )


# ============================================================
# CENTER
# ============================================================

with center:

    st.markdown(
        """
        <div class="co-hero">

            <div class="co-kicker">
                CareerOps AI
            </div>

            <div class="co-hero-title">
                Career Assistant AI
            </div>

            <p class="co-hero-sub">
                Configure the model in
                <strong>Settings</strong>.
                Choose an agent and review past
                results in <strong>Analysis</strong>.
            </p>

        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # ========================================================
    # TOP CONTROLS
    # ========================================================

    c1, c2, c3, c4 = st.columns(
        [1.15, 1.15, 0.85, 3.0]
    )

    with c1:

        label_l = (
            "Hide Settings"
            if left_open
            else "Show Settings"
        )

        if st.button(
            label_l,
            key="tog_left",
            use_container_width=True,
        ):

            st.session_state.left_open = (
                not st.session_state.left_open
            )

            st.rerun()

    with c2:

        label_r = (
            "Hide Analysis"
            if right_open
            else "Show Analysis"
        )

        if st.button(
            label_r,
            key="tog_right",
            use_container_width=True,
        ):

            st.session_state.right_open = (
                not st.session_state.right_open
            )

            st.rerun()

    with c3:

        if st.session_state.run_status in (
            "running",
            "error",
        ):

            if st.button(
                "Clear status",
                key="clear_run",
                use_container_width=True,
            ):

                clear_run_state()
                st.rerun()

    with c4:

        st.caption(
            f"Agent: **{selected_agent}**"
            + (
                " · run active"
                if run_busy
                else ""
            )
        )

    st.markdown(
        f"""
        <span class="co-agent-pill">
            {selected_agent}
        </span>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        AGENT_DESCRIPTIONS.get(
            selected_agent,
            "",
        )
    )


    # ========================================================
    # RUN STATUS
    # ========================================================

    if st.session_state.run_status == "running":

        st.info(
            f"Running "
            f"**{st.session_state.selected_agent}**… "
            "Wait for completion, or press "
            "**Clear status** if this is stuck."
        )

        if st.session_state.run_started_at:

            st.caption(
                "Started at "
                f"{st.session_state.run_started_at}"
            )

    elif st.session_state.run_status == "error":

        st.error(
            "The last run failed."
        )

        if st.session_state.run_error:

            with st.expander(
                "Error details",
                expanded=True,
            ):

                st.code(
                    st.session_state.run_error
                )

        st.caption(
            "Fix the issue, then run again."
        )

    elif st.session_state.run_status == "success":

        st.success(
            "Last run completed. "
            "Output is below and in Insight Archive."
        )


    # ========================================================
    # TABS
    # ========================================================

    tab_cv, tab_job, tab_run = st.tabs(
        [
            "CV",
            "Job description",
            "Run",
        ]
    )


    # ========================================================
    # CV
    # ========================================================

    with tab_cv:

        st.markdown(
            '<div class="co-field-label">'
            "Candidate CV"
            "</div>",
            unsafe_allow_html=True,
        )

        cv_upload = st.file_uploader(
            "Upload CV",
            type=[
                "pdf",
                "docx",
                "txt",
            ],
            help="PDF, DOCX, or TXT",
            label_visibility="collapsed",
        )

        if cv_upload is not None:

            try:

                ext = os.path.splitext(
                    cv_upload.name
                )[1].lower()

                if ext == ".txt":

                    st.session_state.cv_text = (
                        cv_upload.read()
                        .decode(
                            "utf-8",
                            errors="ignore",
                        )
                    )

                else:

                    with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=ext,
                    ) as tmp:

                        tmp.write(
                            cv_upload.getbuffer()
                        )

                        path = tmp.name

                    try:

                        extracted = (
                            extract_cv_text.run(
                                path
                            )
                        )

                        if extracted:

                            st.session_state.cv_text = (
                                extracted
                            )

                    finally:

                        try:
                            os.remove(path)
                        except Exception:
                            pass

                st.success(
                    f"Loaded {cv_upload.name}"
                )

            except Exception as err:

                st.error(
                    f"Could not read CV: {err}"
                )

        st.session_state.cv_text = st.text_area(
            "CV text",
            value=st.session_state.cv_text,
            height=220,
            placeholder="Paste CV text…",
            label_visibility="collapsed",
        )


    # ========================================================
    # JOB DESCRIPTION
    # ========================================================

    with tab_job:

        st.markdown(
            '<div class="co-field-label">'
            "Job description"
            "</div>",
            unsafe_allow_html=True,
        )

        st.session_state.job_description = (
            st.text_area(
                "Job description",
                value=(
                    st.session_state.job_description
                ),
                height=280,
                placeholder=(
                    "Paste the full job description…"
                ),
                label_visibility="collapsed",
            )
        )


    # ========================================================
    # RUN
    # ========================================================

    with tab_run:

        st.markdown(
            '<div class="co-field-label">'
            "Run analysis"
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"**Selected:** `{selected_agent}`"
        )

        if (
            st.session_state.career_request.strip()
        ):

            st.caption(
                "Optional briefing will be included."
            )

        else:

            st.caption(
                "No extra briefing — standard "
                "task for this agent."
            )

        run_clicked = st.button(
            f"Run {selected_agent}",
            type="primary",
            use_container_width=True,
            disabled=run_busy,
            key="run_main",
        )

        if run_clicked and not run_busy:

            if not MODEL_READY:

                st.session_state.run_status = (
                    "error"
                )

                st.session_state.run_error = (
                    "Selected model is not available. "
                    "Open Settings and configure "
                    "a valid Gemini API key."
                )

                st.rerun()

            else:

                errors = validate_inputs()

                if errors:

                    for error_message in errors:
                        st.warning(
                            error_message
                        )

                else:

                    st.session_state.run_status = (
                        "running"
                    )

                    st.session_state.run_error = ""

                    st.session_state.run_started_at = (
                        datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    )

                    try:

                        with st.spinner(
                            f"Running {selected_agent}… "
                            "Temporary API errors are "
                            "handled automatically."
                        ):

                            result = run_selected_agent(
                                agent_name=selected_agent,
                                cv_text=(
                                    st.session_state.cv_text
                                ),
                                job_description=(
                                    st.session_state.job_description
                                ),
                                career_request=(
                                    st.session_state.career_request
                                ),
                            )

                            result_text = (
                                extract_result_text(
                                    result
                                )
                            )

                            st.session_state.result = (
                                result_text
                            )

                            st.session_state.result_agent = (
                                selected_agent
                            )

                            st.session_state.last_run_time = (
                                datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )
                            )

                            archive_insight(
                                selected_agent,
                                result_text,
                                st.session_state.career_request,
                            )

                            st.session_state.run_status = (
                                "success"
                            )

                            st.session_state.run_error = ""

                    except Exception as error:

                        st.session_state.run_status = (
                            "error"
                        )

                        if is_daily_quota_error(
                            error
                        ):

                            st.session_state.run_error = (
                                "Gemini quota / usage "
                                "limit reached.\n\n"
                                + str(error)
                            )

                        else:

                            st.session_state.run_error = (
                                str(error)
                            )

                    finally:

                        st.session_state.run_started_at = (
                            None
                        )

                        if (
                            st.session_state.run_status
                            == "running"
                        ):

                            st.session_state.run_status = (
                                "error"
                            )

                            st.session_state.run_error = (
                                "Run ended unexpectedly "
                                "without a result."
                            )

                        st.rerun()


    # ========================================================
    # DISPLAY RESULT
    # ========================================================

    active = get_active_insight()

    display_text = (
        st.session_state.result
    )

    display_agent = (
        st.session_state.result_agent
    )

    display_time = (
        st.session_state.last_run_time
    )

    if active and not display_text:

        display_text = active["text"]

        display_agent = active["agent"]

        display_time = active["time"]


    if display_text:

        st.markdown("---")

        st.markdown(
            '<div class="co-section-label">'
            "Insight"
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"**{display_agent}**"
        )

        if display_time:

            st.caption(
                f"Generated {display_time}"
            )

        render_modular_result(
            display_agent,
            display_text,
        )

        safe = (
            display_agent
            .lower()
            .replace(" ", "_")
        )

        match_for_pdf = (
            parse_match_score(
                display_text
            )
            if display_agent
            == "Job Match Score"
            else None
        )

        try:

            pdf_bytes = build_pdf(
                agent=display_agent,
                task=display_agent,
                markdown_text=display_text,
                generated_at=(
                    display_time or ""
                ),
                career_request=(
                    st.session_state.career_request
                    or ""
                ),
                match_score=match_for_pdf,
            )

            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=(
                    f"careerops_{safe}_report.pdf"
                ),
                mime="application/pdf",
                use_container_width=True,
            )

        except Exception as pdf_error:

            st.download_button(
                "Download text",
                data=display_text,
                file_name=(
                    f"careerops_{safe}_report.txt"
                ),
                mime="text/plain",
                use_container_width=True,
            )

            with st.expander(
                "PDF unavailable"
            ):

                st.code(
                    str(pdf_error)
                )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )
