from __future__ import annotations

import copy
import os
import streamlit as st
from contracts.sample import SAMPLE_STATE
from contracts.schemas import AppState
from storage.db import authenticate_user, create_user, load_state
from ui.tab_assessment import render_assessment_tab
from ui.tab_gap import render_gap_tab
from ui.tab_mentor import render_mentor_tab
from ui.tab_profile import render_profile_tab
from ui.tab_requirements import render_requirements_tab
from ui.tab_roadmap import render_roadmap_tab
from ui.dashboard import render_dashboard

st.set_page_config(
    page_title="SkillForce - Career Accelerator",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = "Dark"


def _inject_theme_css(theme: str) -> None:
    is_dark = theme == "Dark"
    if is_dark:
        vars_css = """
          --sf-bg: #0b1220;
          --sf-bg-2: #111827;
          --sf-surface: rgba(17, 24, 39, 0.88);
          --sf-surface-strong: #111827;
          --sf-border: rgba(148, 163, 184, 0.18);
          --sf-text: #e5e7eb;
          --sf-muted: #94a3b8;
          --sf-heading: #f8fafc;
          --sf-accent: #60a5fa;
          --sf-accent-2: #38bdf8;
          --sf-shadow: 0 8px 24px rgba(2, 6, 23, 0.35);
          --sf-grad-a: rgba(96,165,250,0.16);
          --sf-grad-b: rgba(56,189,248,0.12);
          --sf-tab-active: #93c5fd;
          --sf-pill-bg: rgba(96,165,250,0.16);
          --sf-pill-text: #bfdbfe;
        """
    else:
        vars_css = """
          --sf-bg: #f8fafc;
          --sf-bg-2: #ffffff;
          --sf-surface: rgba(255, 255, 255, 0.92);
          --sf-surface-strong: #ffffff;
          --sf-border: rgba(15, 23, 42, 0.1);
          --sf-text: #0f172a;
          --sf-muted: #475569;
          --sf-heading: #0b1220;
          --sf-accent: #2563eb;
          --sf-accent-2: #0ea5e9;
          --sf-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
          --sf-grad-a: rgba(37,99,235,0.08);
          --sf-grad-b: rgba(14,165,233,0.08);
          --sf-tab-active: #1d4ed8;
          --sf-pill-bg: #dbeafe;
          --sf-pill-text: #1e3a8a;
        """

    st.markdown(
        f"""
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700&display=swap');
          :root {{
            {vars_css}
          }}
          html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: var(--sf-text);
          }}
          .stApp {{
            background:
              radial-gradient(1200px 420px at 100% -10%, var(--sf-grad-a), transparent 60%),
              radial-gradient(900px 320px at -10% 0%, var(--sf-grad-b), transparent 55%),
              linear-gradient(180deg, var(--sf-bg) 0%, var(--sf-bg-2) 100%);
            transition: background 240ms ease, color 240ms ease;
          }}
          .block-container {{ padding-top: 1.4rem; padding-bottom: 2.75rem; max-width: 1320px; }}
          h1 {{
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
            font-size: 2.1rem; font-weight: 700; margin-bottom: 0.2rem; letter-spacing: -0.03em;
            color: var(--sf-heading);
          }}
          h2, h3 {{
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
            letter-spacing: -0.02em;
            color: var(--sf-heading);
          }}
          [data-testid="stCaptionContainer"] p, .stCaption {{ color: var(--sf-muted); }}
          [data-testid="stSidebar"] {{
            border-right: 1px solid var(--sf-border);
            background: linear-gradient(180deg, var(--sf-bg-2) 0%, var(--sf-bg) 100%);
          }}
          [data-testid="stSidebar"] .block-container {{ padding-top: 1rem; }}
          [data-testid="stMetric"] {{
            background: var(--sf-surface);
            border: 1px solid var(--sf-border);
            border-radius: 14px;
            padding: 0.75rem 0.9rem;
            box-shadow: var(--sf-shadow);
            transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
          }}
          [data-testid="stMetric"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 24px rgba(2, 6, 23, 0.18);
            border-color: rgba(96,165,250,0.35);
          }}
          [data-testid="stMetricLabel"] {{ font-weight: 600; color: var(--sf-muted); }}
          [data-testid="stMetricValue"] {{ color: var(--sf-heading); }}
          .stTabs [data-baseweb="tab-list"] {{
            gap: 0.45rem;
            border-bottom: 1px solid var(--sf-border);
            padding-bottom: 0.3rem;
          }}
          .stTabs [data-baseweb="tab"] {{
            border-radius: 10px 10px 0 0;
            padding: 0.55rem 1rem;
            font-weight: 600;
            color: var(--sf-muted);
            transition: color 180ms ease, background 180ms ease;
          }}
          .stTabs [aria-selected="true"] {{ color: var(--sf-tab-active); }}
          div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 14px;
            border-color: var(--sf-border);
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
            background: var(--sf-surface);
            transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
          }}
          .stButton > button {{
            border-radius: 10px;
            font-weight: 600;
            border: 1px solid var(--sf-border);
            color: var(--sf-text);
            background: var(--sf-surface-strong);
            transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
          }}
          .stButton > button:hover {{
            transform: translateY(-1px);
            border-color: rgba(96,165,250,0.35);
          }}
          .stButton > button[kind="primary"] {{
            background: linear-gradient(180deg, var(--sf-accent) 0%, #2563eb 100%);
            border: 1px solid rgba(37,99,235,0.7);
            color: #ffffff;
            box-shadow: 0 6px 14px rgba(37, 99, 235, 0.25);
          }}
          .stButton > button[kind="primary"]:hover {{
            box-shadow: 0 10px 18px rgba(37, 99, 235, 0.3);
          }}
          [data-baseweb="input"] input, [data-baseweb="textarea"] textarea, [data-baseweb="select"] > div {{
            border-radius: 10px;
          }}
          .skillforce-muted {{ color: var(--sf-muted); font-size: 0.92rem; }}
          .skillforce-pill {{
            display: inline-block; padding: 0.22rem 0.65rem; border-radius: 999px;
            font-size: 0.75rem; font-weight: 700; background: var(--sf-pill-bg); color: var(--sf-pill-text);
            border: 1px solid var(--sf-border);
            letter-spacing: 0.01em;
          }}
          @keyframes sf-fade-up {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
          }}
          @keyframes sf-fade-in {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
          }}
          .sf-animate {{
            animation: sf-fade-up 420ms ease both;
          }}
          .sf-animate-slow {{
            animation: sf-fade-up 560ms ease both;
          }}
          .sf-fade {{
            animation: sf-fade-in 380ms ease both;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


_inject_theme_css(st.session_state.ui_theme)

FIXTURE_MODE = os.environ.get("UI_FIXTURE", "1") == "1"


def _profile_complete(state: AppState) -> bool:
    profile = state.profile
    has_target = bool((profile.target_role or "").strip())
    has_name = bool((profile.name or "").strip())
    has_skills = bool(profile.skills)
    return has_target and has_name and has_skills


def _ensure_demo_user() -> tuple[str, str]:
    demo_username = "demo"
    demo_password = "demo123"
    try:
        create_user(demo_username, demo_password)
    except Exception:
        # User may already exist; authentication below will validate access.
        pass
    return demo_username, demo_password


def _render_auth() -> None:
    st.title("SkillForce: Career Accelerator")
    st.caption("Sign in or create an account to build your personalized career roadmap.")

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("### Welcome to SkillForce")
            st.write(
                "1. **Create your account** and sign in securely.\n"
                "2. **Complete your profile** with skills, experience, and target role.\n"
                "3. **Generate your personalized roadmap** and track progress with assessments."
            )
            st.info("Your profile and progress are saved to your account.")

        if FIXTURE_MODE:
            with st.container(border=True):
                st.markdown("#### Demo access")
                st.caption("Use the demo account to explore the app quickly with sample data.")
                if st.button("Continue with demo account", type="secondary", use_container_width=True):
                    demo_username, demo_password = _ensure_demo_user()
                    if authenticate_user(demo_username, demo_password):
                        st.session_state.authenticated_user = demo_username
                        st.session_state.pop("state", None)
                        st.session_state.pop("auth_user_id", None)
                        st.success("Signed in with demo account.")
                        st.rerun()
                    else:
                        st.error("Unable to sign in to the demo account. Please try again.")

    with right:
        login_tab, signup_tab = st.tabs(["Sign in", "Create account"])

        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="e.g. aarav")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
            if submitted:
                if not username.strip() or not password:
                    st.error("Please enter both username and password.")
                elif authenticate_user(username.strip(), password):
                    st.session_state.authenticated_user = username.strip()
                    st.session_state.pop("state", None)
                    st.session_state.pop("auth_user_id", None)
                    st.success("Signed in successfully.")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        with signup_tab:
            with st.form("signup_form"):
                new_username = st.text_input("Username", key="signup_username", placeholder="Choose a username")
                new_password = st.text_input("Password", type="password", key="signup_password")
                confirm_password = st.text_input("Confirm password", type="password", key="signup_confirm")
                created = st.form_submit_button("Create account", type="primary", use_container_width=True)
            if created:
                if not new_username.strip():
                    st.error("Please choose a username.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    try:
                        create_user(new_username.strip(), new_password)
                        st.session_state.authenticated_user = new_username.strip()
                        st.session_state.pop("state", None)
                        st.session_state.pop("auth_user_id", None)
                        st.success("Account created. You are now signed in.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))


def _load_app_state(user_id: str) -> AppState:
    if FIXTURE_MODE and user_id == "demo":
        state = copy.deepcopy(SAMPLE_STATE)
        if not (state.profile.name or "").strip():
            state.profile.name = "Demo User"
        return state
    state = load_state(user_id)
    if not (state.profile.name or "").strip():
        state.profile.name = user_id
    return state


# Optional auto-auth for testing/automation (authentication UI remains available otherwise)
auto_auth_user = os.environ.get("SKILLFORCE_AUTH_USER", "").strip()
if auto_auth_user and not st.session_state.get("authenticated_user"):
    if FIXTURE_MODE:
        _ensure_demo_user() if auto_auth_user == "demo" else None
    st.session_state.authenticated_user = auto_auth_user

# Authentication gate
if not st.session_state.get("authenticated_user"):
    _render_auth()
    st.stop()

user_id = str(st.session_state.get("authenticated_user") or "Aarav").strip() or "Aarav"

# Initialize or reload AppState for the active user
if "state" not in st.session_state or st.session_state.get("auth_user_id") != user_id:
    st.session_state.state = _load_app_state(user_id)
    st.session_state.auth_user_id = user_id

state: AppState = st.session_state.state

st.title("SkillForce: Career Accelerator")
st.caption("Analyze your profile, close skill gaps, and adapt your roadmap with confidence.")

# Persistent Sidebar: profile snapshot and live Agent Activity Log, newest first
with st.sidebar:
    st.title("🧭 SkillForce")
    st.caption("Agentic Career Acceleration & Upskilling Platform")

    selected_theme = st.selectbox(
        "Appearance",
        options=["Dark", "Light"],
        index=["Dark", "Light"].index(st.session_state.ui_theme)
        if st.session_state.ui_theme in ["Dark", "Light"]
        else 0,
        help="Switch between dark and light theme.",
    )
    if selected_theme != st.session_state.ui_theme:
        st.session_state.ui_theme = selected_theme
        st.rerun()

    profile = state.profile
    target_role = profile.target_role or "Not set"
    target_company = profile.target_company or "Any company"
    mode_label = "Sample fixture" if FIXTURE_MODE else "Authenticated account"
    st.markdown(
        f"<span class='skillforce-pill'>{mode_label}</span>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("**Learner**")
        st.write(profile.name or user_id)
        st.markdown("**Account**")
        st.write(user_id)
        st.markdown("**Target**")
        st.write(f"{target_role} · {target_company}")
        if state.gap is not None:
            st.metric("Readiness", f"{state.gap.match_percent:g}%")

    if not FIXTURE_MODE:
        if st.button("Log out", use_container_width=True):
            for key in [
                "authenticated_user",
                "auth_user_id",
                "state",
                "latest_explanation",
                "mentor_chat_history",
                "mentor_chat_target",
                "current_quiz",
                "active_quiz_skill",
                "last_assessment_result",
                "roadmap_task_checks",
            ]:
                st.session_state.pop(key, None)
            st.rerun()

    st.divider()

    st.subheader("📋 Agent Activity Log")
    st.caption("Real-time audit log of agent operations (newest first).")

    if state.log:
        for entry in reversed(state.log[-30:]):
            with st.container(border=True):
                col1, col2 = st.columns([1, 1])
                col1.markdown(f"**`{entry.agent}`**")
                time_str = entry.timestamp[:19].replace("T", " ") if entry.timestamp else ""
                col2.caption(time_str)
                st.markdown(f"*{entry.action}*")
                st.write(entry.reason)
        if len(state.log) > 30:
            st.caption(f"Showing latest 30 of {len(state.log)} log entries.")
    else:
        st.caption("No agent activity logged yet.")

profile_ready = _profile_complete(state)

if not profile_ready:
    st.info(
        "Complete your profile first to unlock your personalized dashboard, requirements, gap analysis, and roadmap. "
        "Add your name, skills, and target role, then click **Save Profile**."
    )
    render_profile_tab(state, user_id)
    st.stop()

# Main content: 7 tabs with Dashboard FIRST
tab_labels = [
    "Dashboard",
    "Profile",
    "Requirements",
    "Gap",
    "Roadmap",
    "Assessment",
    "Mentor",
]
tabs = st.tabs(tab_labels)

with tabs[0]:
    render_dashboard(state)

with tabs[1]:
    render_profile_tab(state, user_id)

with tabs[2]:
    render_requirements_tab(state)

with tabs[3]:
    render_gap_tab(state)

with tabs[4]:
    render_roadmap_tab(state)

with tabs[5]:
    render_assessment_tab(state, user_id)

with tabs[6]:
    render_mentor_tab(state, user_id)
