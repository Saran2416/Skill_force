from __future__ import annotations

import copy
import os
import streamlit as st
from contracts.sample import SAMPLE_STATE
from contracts.schemas import AppState
from storage.db import load_state
from ui.tab_assessment import render_assessment_tab
from ui.tab_dashboard import render_dashboard_tab
from ui.tab_gap import render_gap_tab
from ui.tab_mentor import render_mentor_tab
from ui.tab_profile import render_profile_tab
from ui.tab_requirements import render_requirements_tab
from ui.tab_roadmap import render_roadmap_tab

st.set_page_config(
    page_title="SkillPath - Career Accelerator",
    page_icon="🧭",
    layout="wide",
)

USER_ID = "Aarav"

# Initialize AppState
if "state" not in st.session_state:
    if os.environ.get("UI_FIXTURE", "1") == "1":
        st.session_state.state = copy.deepcopy(SAMPLE_STATE)
    else:
        st.session_state.state = load_state(USER_ID)

state: AppState = st.session_state.state

# Persistent Sidebar: live Agent Activity Log, newest first
with st.sidebar:
    st.title("🧭 SkillPath")
    st.caption("Agentic Career Acceleration & Upskilling Platform")
    st.divider()

    st.subheader("📋 Agent Activity Log")
    st.caption("Real-time audit log of agent operations (newest first).")

    if state.log:
        for entry in reversed(state.log):
            with st.container(border=True):
                col1, col2 = st.columns([1, 1])
                col1.markdown(f"**`{entry.agent}`**")
                time_str = entry.timestamp[:19].replace("T", " ") if entry.timestamp else ""
                col2.caption(time_str)
                st.markdown(f"*{entry.action}*")
                st.write(entry.reason)
    else:
        st.caption("No agent activity logged yet.")

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
    render_dashboard_tab(state)

with tabs[1]:
    render_profile_tab(state, USER_ID)

with tabs[2]:
    render_requirements_tab(state)

with tabs[3]:
    render_gap_tab(state)

with tabs[4]:
    render_roadmap_tab(state)

with tabs[5]:
    render_assessment_tab(state, USER_ID)

with tabs[6]:
    render_mentor_tab(state, USER_ID)
