from __future__ import annotations

import streamlit as st
from contracts.schemas import AppState

_STATUS_BADGES = {
    "todo": "⏳ To Do",
    "doing": "🚀 In Progress",
    "done": "✅ Completed",
    "revision": "⚠️ Needs Revision",
}


def render_roadmap_tab(state: AppState) -> None:
    """Render the personalized learning roadmap tab with ordered steps and revision highlights."""
    roadmap = getattr(state, "roadmap", None)
    if roadmap is None or not roadmap.steps:
        st.info("No learning roadmap generated yet. Complete your profile to build your plan.")
        return

    st.subheader("Learning Roadmap")
    if roadmap.est_hours:
        st.caption(f"⏱️ **Total Estimated Time:** ~{roadmap.est_hours} hours to job readiness")

    steps = sorted(roadmap.steps, key=lambda s: s.order)

    for step in steps:
        is_revision = step.status == "revision"
        status_label = _STATUS_BADGES.get(step.status, step.status.upper())

        with st.container(border=True):
            col_title, col_status = st.columns([3, 1])
            with col_title:
                st.markdown(
                    f"### Step {step.order}: **{step.skill}** "
                    f"<span style='font-size:0.9rem;color:#6b7280;'>(Target: Level {step.target_level}/5)</span>",
                    unsafe_allow_html=True,
                )
            with col_status:
                if is_revision:
                    st.error(status_label)
                elif step.status == "done":
                    st.success(status_label)
                elif step.status == "doing":
                    st.info(status_label)
                else:
                    st.caption(status_label)

            if is_revision:
                st.warning(
                    "⚠️ **Revision Required:** Assessment results flagged this skill for review. "
                    "Review foundational concepts and complete the practice tasks before retaking."
                )

            # Mini project
            if step.mini_project:
                st.markdown(f"🛠️ **Mini-Project:** {step.mini_project}")

            # Practice tasks
            if step.practice_tasks:
                st.markdown("**Practice Tasks:**")
                for task in step.practice_tasks:
                    st.markdown(f"- [ ] {task}")

            # Resource links
            if step.resources:
                st.markdown("**Learning Resources:**")
                for res in step.resources:
                    st.markdown(f"- [{res.title}]({res.url})")
