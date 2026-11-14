from __future__ import annotations

import streamlit as st
from contracts.schemas import AppState


def _render_confidence_badge(confidence: str) -> None:
    if confidence == "curated":
        badge_html = (
            "<span style='background:#1a7f37;color:#ffffff;padding:3px 12px;"
            "border-radius:12px;font-size:0.8rem;font-weight:600;'>Curated</span>"
        )
    else:
        badge_html = (
            "<span style='background:#b7791f;color:#ffffff;padding:3px 12px;"
            "border-radius:12px;font-size:0.8rem;font-weight:600;'>AI-estimated</span>"
        )
    st.markdown(badge_html, unsafe_allow_html=True)


def render_requirements_tab(state: AppState) -> None:
    """Render the Target Role Requirements tab."""
    req = getattr(state, "requirements", None)
    if req is None:
        st.info("No requirements available yet. Complete your profile to load role requirements.")
        return

    company_label = req.company or "Any Company"
    st.subheader(f"Requirements: {req.role} at {company_label}")

    # Confidence badge
    _render_confidence_badge(req.confidence)

    # Disclaimer
    if req.disclaimer:
        st.info(f"ℹ️ **Disclaimer:** {req.disclaimer}")

    # Requirements Table
    st.markdown("#### Skill Requirements")
    if req.requirements:
        table_data = [
            {
                "Skill": r.skill,
                "Required Level": f"{r.level_required}/5",
                "Priority": r.priority.upper(),
                "Note": r.note,
            }
            for r in req.requirements
        ]
        st.table(table_data)
    else:
        st.caption("No specific skills listed for this role.")

    # Two columns for Tools & Certs
    col_tools, col_certs = st.columns(2)
    with col_tools:
        st.markdown("#### Required Tools & Technologies")
        if req.tools:
            for tool in req.tools:
                st.markdown(f"- **{tool}**")
        else:
            st.caption("No specific tools specified.")

    with col_certs:
        st.markdown("#### Recommended Certifications")
        if req.certs:
            for cert in req.certs:
                st.markdown(f"- **{cert}**")
        else:
            st.caption("No specific certifications required.")

    # Interview Process
    st.markdown("#### Interview Process")
    if req.interview_process:
        for idx, stage in enumerate(req.interview_process, 1):
            st.markdown(f"**Step {idx}:** {stage}")
    else:
        st.caption("Standard technical and behavioral interview process.")

    # Additional Recommendations List
    st.markdown("#### Additional Recommendations")
    recommendations = getattr(state, "recommendations", [])
    if recommendations:
        for rec in recommendations:
            with st.container(border=True):
                col_title, col_effort = st.columns([3, 1])
                type_label = rec.type.replace("_", " ").title()
                col_title.markdown(f"**{rec.title}** `{type_label}`")
                col_effort.caption(f"⏱️ Effort: ~{rec.effort_hours}h")
                st.write(rec.why)
    else:
        st.caption("No additional recommendations generated yet.")
