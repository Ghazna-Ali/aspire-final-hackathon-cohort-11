import os
import re
import time
import tempfile
import uuid
from datetime import datetime

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
# CSS — panels, rails, scroll regions
# ============================================================
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] { background: transparent; }
    div[data-testid="stToolbar"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .block-container {
        padding-top: 0.85rem;
        padding-bottom: 1.5rem;
        max-width: 1600px;
    }

    /* Panel scroll areas (approximate independent scroll) */
    .co-scroll {
        max-height: calc(100vh - 5.5rem);
        overflow-y: auto;
        overflow-x: hidden;
        padding-right: 0.35rem;
        scrollbar-width: thin;
        scrollbar-color: #94a3b8 transparent;
    }
    .co-scroll::-webkit-scrollbar { width: 6px; }
    .co-scroll::-webkit-scrollbar-thumb {
        background: #94a3b8;
        border-radius: 999px;
    }

    .co-rail {
        background: #0f172a;
        border-radius: 10px;
        padding: 0.55rem 0.35rem;
        text-align: center;
        min-height: 280px;
    }
    .co-rail-label {
        font-size: 0.65rem;
        color: #94a3b8;
        letter-spacing: 0.04em;
        margin-top: 0.15rem;
        line-height: 1.2;
    }

    .co-card-dark {
        background: #0f172a;
        color: #f8fafc;
        border-radius: 10px;
        padding: 1rem 1.15rem;
        margin-bottom: 0.85rem;
    }
    .co-kicker {
        font-size: 0.68rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #94a3b8;
        font-weight: 600;
    }
    .co-section-label {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #64748b;
        margin: 0.35rem 0 0.35rem 0;
    }
    .co-muted { color: #64748b; font-size: 0.82rem; }
    .co-agent-pill {
        display: inline-block;
        background: #eef2ff;
        color: #3730a3;
        border-radius: 999px;
        padding: 0.22rem 0.7rem;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 0.35rem 0 0.5rem 0;
    }
    .co-field-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #334155;
        margin-bottom: 0.25rem;
    }

    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        border: 1px solid #cbd5e1;
        background: #ffffff;
        color: #0f172a;
    }
    div.stButton > button[kind="primary"] {
        background: #1e293b;
        color: #ffffff;
        border: 1px solid #1e293b;
    }
    div.stButton > button:hover { border-color: #94a3b8; }
    div.stButton > button[kind="primary"]:hover {
        background: #0f172a;
        border-color: #0f172a;
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
    "is_running": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def reset_result():
    st.session_state.result = ""
    st.session_state.result_agent = ""
    st.session_state.last_run_time = None
    st.session_state.active_insight_id = None


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
    st.session_state.is_running = False


def archive_insight(agent_name, text, career_request=""):
    item = {
        "id": str(uuid.uuid4()),
        "agent": agent_name,
        "text": text,
        "career_request": career_request,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    st.session_state.insight_archive.insert(0, item)
    st.session_state.insight_archive = st.session_state.insight_archive[:30]
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
    return any(p in message for p in patterns)


def is_retryable_ai_error(error):
    if is_daily_quota_error(error):
        return False
    message = str(error).upper()
    patterns = [
        "503", "SERVICE_UNAVAILABLE", "UNAVAILABLE", "429",
        "RESOURCE_EXHAUSTED", "RATE_LIMIT", "TOO MANY REQUESTS",
        "500", "502", "504", "INTERNAL SERVER ERROR",
        "BAD GATEWAY", "GATEWAY TIMEOUT",
    ]
    return any(p in message for p in patterns)


def kickoff_with_retry(crew, inputs, max_attempts=4):
    delays = [5, 15, 30]
    for attempt in range(max_attempts):
        try:
            return crew.kickoff(inputs=inputs)
        except Exception as error:
            if is_daily_quota_error(error) or not is_retryable_ai_error(error):
                raise error
            if attempt == max_attempts - 1:
                raise error
            delay = delays[min(attempt, len(delays) - 1)]
            st.warning(f"Temporary service issue. Retrying in {delay}s…")
            time.sleep(delay)


def create_single_agent_crew(agent_name):
    if agent_name not in AGENTS:
        raise ValueError(f"Unknown agent: {agent_name}")
    if agent_name not in TASKS:
        raise ValueError(f"No task configured for: {agent_name}")
    return Crew(
        agents=[AGENTS[agent_name]],
        tasks=[TASKS[agent_name]],
        process=Process.sequential,
        verbose=True,
    )


def run_selected_agent(agent_name, cv_text, job_description, career_request):
    crew = create_single_agent_crew(agent_name)
    inputs = {
        "cv_text": cv_text or "(not provided)",
        "job_description": job_description or "(not provided)",
        "career_request": career_request
        or "Produce the standard analysis for this agent.",
    }
    try:
        memory = CareerMemory()
        if hasattr(memory, "set_cv"):
            memory.set_cv(cv_text)
        if hasattr(memory, "set_job_description"):
            memory.set_job_description(job_description)
        if hasattr(memory, "set_career_request"):
            memory.set_career_request(career_request)
    except Exception:
        pass
    return kickoff_with_retry(crew, inputs)


def extract_result_text(result):
    if result is None:
        return ""
    if hasattr(result, "raw") and result.raw is not None:
        return str(result.raw)
    return str(result)


def show_quota_error(error):
    st.error("The selected provider hit a quota or usage limit.")
    with st.expander("Details"):
        st.code(str(error))


def validate_inputs():
    errors = []
    if not st.session_state.cv_text.strip():
        errors.append("Add your CV (upload or paste).")
    if not st.session_state.job_description.strip():
        errors.append("Add the job description.")
    return errors


def render_modular_result(agent_name, text):
    if not text:
        st.info("No content.")
        return

    if agent_name == "Job Match Score":
        match = parse_match_score(text)
        if match:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Match", f"{match['overall']}%")
                st.progress(match["overall"] / 100.0)
            with c2:
                if match.get("breakdown"):
                    cols = st.columns(len(match["breakdown"]))
                    for col, (cat, val) in zip(cols, match["breakdown"].items()):
                        col.metric(cat.split()[0], f"{val}")

    if agent_name == "Job Legitimacy Check":
        m = re.search(r"Legitimacy Score:\s*(\d{1,3})", text, re.I)
        if m:
            score = min(100, max(0, int(m.group(1))))
            st.metric("Legitimacy score", f"{score}/100")
            st.progress(score / 100.0)

    sections = re.split(r"(?m)^##\s+", text)
    if len(sections) > 1:
        st.markdown(
            '<div class="co-section-label">Modules</div>',
            unsafe_allow_html=True,
        )
        for block in sections[1:]:
            lines = block.strip().split("\n", 1)
            title = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ""
            with st.expander(title, expanded=False):
                st.markdown(body if body else "_No detail._")
        with st.expander("Full report", expanded=False):
            st.markdown(text)
    else:
        with st.expander("Full report", expanded=True):
            st.markdown(text)


# ============================================================
# COLUMN WIDTHS based on open/closed panels
# ============================================================
# Layout slots: [left_rail | left_panel? | center | right_panel? | right_rail]
left_open = st.session_state.left_open
right_open = st.session_state.right_open

# Narrow rails always present (~0.28); panels ~1.1 when open
widths = [0.32]
if left_open:
    widths.append(1.15)
widths.append(2.5)
if right_open:
    widths.append(1.15)
widths.append(0.32)

cols = st.columns(widths, gap="small")

# Map indices
idx = 0
left_rail = cols[idx]
idx += 1
left_panel = None
if left_open:
    left_panel = cols[idx]
    idx += 1
center = cols[idx]
idx += 1
right_panel = None
if right_open:
    right_panel = cols[idx]
    idx += 1
right_rail = cols[idx]

MODEL_READY = False
selected_agent = st.session_state.selected_agent

# ============================================================
# LEFT RAIL (always visible)
# ============================================================
with left_rail:
    st.markdown('<div class="co-rail">', unsafe_allow_html=True)

    tip_left = "Collapse workspace" if left_open else "Open workspace (model & status)"
    if st.button("☰", key="toggle_left", help=tip_left, use_container_width=True):
        st.session_state.left_open = not st.session_state.left_open
        st.rerun()
    st.markdown(
        '<div class="co-rail-label">Workspace</div>',
        unsafe_allow_html=True,
    )

    # Model icon — opens left if closed
    if st.button("◈", key="rail_model", help="Model settings", use_container_width=True):
        st.session_state.left_open = True
        st.rerun()
    st.markdown(
        '<div class="co-rail-label">Model</div>',
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# LEFT PANEL
# ============================================================
if left_panel is not None:
    with left_panel:
        st.markdown('<div class="co-scroll">', unsafe_allow_html=True)

        top_l1, top_l2 = st.columns([4, 1])
        with top_l1:
            st.markdown(
                '<div class="co-section-label">Workspace</div>',
                unsafe_allow_html=True,
            )
        with top_l2:
            if st.button("⟨", key="close_left", help="Collapse left panel"):
                st.session_state.left_open = False
                st.rerun()

        MODEL_READY = render_model_selector(AGENTS, container=left_panel)

        st.markdown(
            '<div class="co-section-label">Status</div>',
            unsafe_allow_html=True,
        )
        if MODEL_READY:
            st.success("Model ready")
        else:
            st.warning("Configure an API key")
        st.caption("One agent runs per action. Outputs stay in Insight Archive.")

        st.markdown("---")
        if st.button("Reset workspace", use_container_width=True, key="reset_ws"):
            reset_everything()
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
else:
    # Still need MODEL_READY when left is closed — compute without UI
    from model_manager import is_model_available, default_model_key

    key = st.session_state.get("selected_model_key", default_model_key())
    MODEL_READY = is_model_available(key)
    # Re-apply LLM if possible so runs still work with panel closed
    if MODEL_READY:
        try:
            from model_manager import configure_agents

            configure_agents(AGENTS, key)
        except Exception:
            MODEL_READY = False

# ============================================================
# RIGHT RAIL (always visible)
# ============================================================
with right_rail:
    st.markdown('<div class="co-rail">', unsafe_allow_html=True)

    tip_right = "Collapse analysis panel" if right_open else "Open analysis panel"
    if st.button("☰", key="toggle_right", help=tip_right, use_container_width=True):
        st.session_state.right_open = not st.session_state.right_open
        st.rerun()
    st.markdown(
        '<div class="co-rail-label">Panel</div>',
        unsafe_allow_html=True,
    )

    agent_hover = f"Analysis type — currently: {st.session_state.selected_agent}"
    if st.button("◉", key="rail_agent", help=agent_hover, use_container_width=True):
        st.session_state.right_open = True
        st.rerun()
    st.markdown(
        '<div class="co-rail-label">Agent</div>',
        unsafe_allow_html=True,
    )

    if st.button("▦", key="rail_archive", help="Insight Archive", use_container_width=True):
        st.session_state.right_open = True
        st.rerun()
    st.markdown(
        '<div class="co-rail-label">Archive</div>',
        unsafe_allow_html=True,
    )

    if st.button("💬", key="rail_brief", help="Context briefing (optional)", use_container_width=True):
        st.session_state.right_open = True
        st.session_state.briefing_open = True
        st.rerun()
    st.markdown(
        '<div class="co-rail-label">Briefing</div>',
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# RIGHT PANEL
# ============================================================
if right_panel is not None:
    with right_panel:
        st.markdown('<div class="co-scroll">', unsafe_allow_html=True)

        top_r1, top_r2 = st.columns([4, 1])
        with top_r1:
            st.markdown(
                '<div class="co-section-label">Analysis</div>',
                unsafe_allow_html=True,
            )
        with top_r2:
            if st.button("⟩", key="close_right", help="Collapse right panel"):
                st.session_state.right_open = False
                st.rerun()

        # While running: discourage changing agent mid-flight
        if st.session_state.is_running:
            st.info(
                f"Running **{st.session_state.selected_agent}**. "
                "Agent selection is locked until this run finishes."
            )
            st.caption(AGENT_DESCRIPTIONS.get(st.session_state.selected_agent, ""))
            selected_agent = st.session_state.selected_agent
        else:
            st.markdown(
                '<div class="co-field-label">Analysis type</div>',
                unsafe_allow_html=True,
            )
            agent_names = list(AGENTS.keys())
            try:
                a_index = agent_names.index(st.session_state.selected_agent)
            except ValueError:
                a_index = 0

            selected_agent = st.selectbox(
                "Analysis type",
                options=agent_names,
                index=a_index,
                label_visibility="collapsed",
                key="agent_select_box",
                help="Choose what to run. Change this before starting a run.",
            )
            st.session_state.selected_agent = selected_agent
            st.caption(AGENT_DESCRIPTIONS.get(selected_agent, ""))

        st.markdown(
            '<div class="co-section-label">Insight Archive</div>',
            unsafe_allow_html=True,
        )
        st.caption("Previous outputs. Switching agents does not delete them.")

        if not st.session_state.insight_archive:
            st.markdown(
                '<p class="co-muted">No saved insights yet.</p>',
                unsafe_allow_html=True,
            )
        else:
            for item in st.session_state.insight_archive[:12]:
                label = f"{item['agent']} · {item['time']}"
                if st.button(label, key=f"arch_{item['id']}", use_container_width=True):
                    st.session_state.active_insight_id = item["id"]
                    st.session_state.result = item["text"]
                    st.session_state.result_agent = item["agent"]
                    st.session_state.last_run_time = item["time"]
                    st.rerun()

        st.markdown("---")
        st.markdown(
            '<div class="co-section-label">Context briefing</div>',
            unsafe_allow_html=True,
        )
        st.caption("Optional guidance for the agent. Not required to run.")

        briefing_open = st.toggle(
            "Show briefing fields",
            value=st.session_state.briefing_open,
            key="briefing_toggle",
        )
        st.session_state.briefing_open = briefing_open

        if briefing_open:
            st.markdown(
                '<div class="co-field-label">Extra instructions</div>',
                unsafe_allow_html=True,
            )
            st.caption("Optional — only used if you fill this in.")
            briefing_text = st.text_area(
                "Extra instructions",
                value=st.session_state.career_request,
                key="career_request_box",
                height=110,
                placeholder=(
                    "Example: Focus on remote roles in Europe. "
                    "Keep answers concise."
                ),
                label_visibility="collapsed",
            )
            st.session_state.career_request = briefing_text

            if st.session_state.insight_archive:
                st.markdown(
                    '<div class="co-field-label">Recent insights</div>',
                    unsafe_allow_html=True,
                )
                for item in st.session_state.insight_archive[:3]:
                    st.markdown(f"- **{item['agent']}** ({item['time']})")

            user_note = st.chat_input("Add a short note for this run")
            if user_note:
                st.session_state.chat_messages.append(
                    {"role": "user", "content": user_note}
                )
                st.session_state.career_request = (
                    (st.session_state.career_request + "\n" + user_note).strip()
                )
                st.rerun()

            for msg in st.session_state.chat_messages[-6:]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

        st.markdown("</div>", unsafe_allow_html=True)
else:
    selected_agent = st.session_state.selected_agent

# ============================================================
# CENTER
# ============================================================
with center:
    st.markdown('<div class="co-scroll">', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="co-card-dark">
            <div class="co-kicker">CareerOps AI</div>
            <div style="font-size:1.35rem;font-weight:700;margin:0.15rem 0 0 0;">
                Career operations workspace
            </div>
            <div style="color:#cbd5e1;font-size:0.88rem;margin-top:0.2rem;">
                Use the side rails to open Model / Agent / Archive / Briefing.
                Add CV and job, then run from the Run tab.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<span class="co-agent-pill">{selected_agent}</span>',
        unsafe_allow_html=True,
    )
    st.caption(AGENT_DESCRIPTIONS.get(selected_agent, ""))

    if st.session_state.is_running:
        st.warning(
            f"Analysis in progress: **{st.session_state.selected_agent}**. "
            "Open the right rail (Agent) after the run to choose a different type."
        )

    tab_cv, tab_job, tab_run = st.tabs(["CV", "Job description", "Run"])

    with tab_cv:
        st.markdown(
            '<div class="co-field-label">Candidate CV</div>',
            unsafe_allow_html=True,
        )
        cv_upload = st.file_uploader(
            "Upload CV",
            type=["pdf", "docx", "txt"],
            help="PDF, DOCX, or TXT",
            label_visibility="collapsed",
        )
        if cv_upload is not None:
            try:
                ext = os.path.splitext(cv_upload.name)[1].lower()
                if ext == ".txt":
                    st.session_state.cv_text = cv_upload.read().decode(
                        "utf-8", errors="ignore"
                    )
                else:
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=ext
                    ) as tmp:
                        tmp.write(cv_upload.getbuffer())
                        path = tmp.name
                    try:
                        extracted = extract_cv_text.run(path)
                        if extracted:
                            st.session_state.cv_text = extracted
                    finally:
                        try:
                            os.remove(path)
                        except Exception:
                            pass
                st.success(f"Loaded {cv_upload.name}")
            except Exception as err:
                st.error(f"Could not read CV: {err}")

        st.session_state.cv_text = st.text_area(
            "CV text",
            value=st.session_state.cv_text,
            height=220,
            placeholder="Paste CV text…",
            label_visibility="collapsed",
        )

    with tab_job:
        st.markdown(
            '<div class="co-field-label">Job description</div>',
            unsafe_allow_html=True,
        )
        st.session_state.job_description = st.text_area(
            "Job description",
            value=st.session_state.job_description,
            height=280,
            placeholder="Paste the full job description…",
            label_visibility="collapsed",
        )

    with tab_run:
        st.markdown(
            '<div class="co-field-label">Run analysis</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**Selected:** `{selected_agent}`")
        if st.session_state.career_request.strip():
            st.caption("Optional briefing will be included.")
        else:
            st.caption("No extra briefing — standard task for this agent.")

        run_disabled = st.session_state.is_running
        run_clicked = st.button(
            f"Run {selected_agent}",
            type="primary",
            use_container_width=True,
            disabled=run_disabled,
            key="run_main",
        )

        if run_clicked and not st.session_state.is_running:
            if not MODEL_READY:
                st.error(
                    "Selected model is not available. "
                    "Open the left rail → Model and fix the API key."
                )
            else:
                errors = validate_inputs()
                if errors:
                    for e in errors:
                        st.warning(e)
                else:
                    st.session_state.is_running = True
                    try:
                        with st.spinner(f"Running {selected_agent}…"):
                            result = run_selected_agent(
                                agent_name=selected_agent,
                                cv_text=st.session_state.cv_text,
                                job_description=st.session_state.job_description,
                                career_request=st.session_state.career_request,
                            )
                            result_text = extract_result_text(result)
                            st.session_state.result = result_text
                            st.session_state.result_agent = selected_agent
                            st.session_state.last_run_time = (
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            )
                            archive_insight(
                                selected_agent,
                                result_text,
                                st.session_state.career_request,
                            )
                            st.success("Complete. Saved to Insight Archive.")
                    except Exception as error:
                        if is_daily_quota_error(error):
                            show_quota_error(error)
                        else:
                            st.error("The agent could not complete this request.")
                            with st.expander("Technical details"):
                                st.code(str(error))
                    finally:
                        st.session_state.is_running = False
                        st.rerun()

    # Active insight
    active = get_active_insight()
    display_text = st.session_state.result
    display_agent = st.session_state.result_agent
    display_time = st.session_state.last_run_time

    if active and not display_text:
        display_text = active["text"]
        display_agent = active["agent"]
        display_time = active["time"]

    if display_text:
        st.markdown("---")
        st.markdown(
            '<div class="co-section-label">Insight</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**{display_agent}**")
        if display_time:
            st.caption(f"Generated {display_time}")

        render_modular_result(display_agent, display_text)

        safe = display_agent.lower().replace(" ", "_")
        match_for_pdf = (
            parse_match_score(display_text)
            if display_agent == "Job Match Score"
            else None
        )
        try:
            pdf_bytes = build_pdf(
                agent=display_agent,
                task=display_agent,
                markdown_text=display_text,
                generated_at=display_time or "",
                career_request=st.session_state.career_request or "",
                match_score=match_for_pdf,
            )
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=f"careerops_{safe}_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as pdf_err:
            st.download_button(
                "Download text",
                data=display_text,
                file_name=f"careerops_{safe}_report.txt",
                mime="text/plain",
                use_container_width=True,
            )
            with st.expander("PDF unavailable"):
                st.code(str(pdf_err))

    st.markdown("</div>", unsafe_allow_html=True)
