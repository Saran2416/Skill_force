from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
from agents.career_matcher import radar_data
from contracts.schemas import AppState


def render_gap_tab(state: AppState) -> None:
    """Render the Skill Gap analysis tab with Plotly radar chart and match %."""
    gap_report = getattr(state, "gap", None)
    if gap_report is None:
        st.info("No skill gap analysis available yet. Save your profile to compute gaps.")
        return

    st.subheader("Skill Gap & Role Readiness")
    st.caption("Compare your current proficiency against target requirements and prioritize what to learn next.")

    # Match % metric
    col_metric, col_summary = st.columns([1, 3], gap="large")
    with col_metric:
        with st.container(border=True):
            st.metric(
                label="Role Match",
                value=f"{gap_report.match_percent:g}%",
                help="Weighted readiness score based on target role requirements.",
            )
    with col_summary:
        st.info(
            "Readiness is weighted by priority: **must-have** skills carry 3× weight, "
            "**good-to-have** 2×, and **bonus** 1×."
        )

    # Plotly radar chart (current vs required)
    st.markdown("#### Competency Radar (Current vs. Required)")
    skills = state.profile.skills if state.profile else []
    chart_data = radar_data(gap_report, state.requirements, skills)

    labels = chart_data.get("labels", [])
    current_vals = chart_data.get("current", [])
    required_vals = chart_data.get("required", [])

    if labels:
        # Loop radar points to close polygon
        theta = labels + [labels[0]]
        r_current = current_vals + [current_vals[0]]
        r_required = required_vals + [required_vals[0]]

        fig = go.Figure()
        fig.add_trace(
            go.Scatterpolar(
                r=r_current,
                theta=theta,
                fill="toself",
                name="Current Level",
                line=dict(color="#2563eb", width=2),
                fillcolor="rgba(37, 99, 235, 0.2)",
            )
        )
        fig.add_trace(
            go.Scatterpolar(
                r=r_required,
                theta=theta,
                fill="toself",
                name="Required Level",
                line=dict(color="#dc2626", width=2, dash="dash"),
                fillcolor="rgba(220, 38, 38, 0.15)",
            )
        )

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 5],
                    tickvals=[0, 1, 2, 3, 4, 5],
                )
            ),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            margin=dict(l=30, r=30, t=30, b=30),
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No radar data available to chart.")

    # Gaps and Strengths Breakdown
    col_gaps, col_strengths = st.columns(2, gap="large")
    with col_gaps:
        with st.container(border=True):
            st.markdown("#### Identified Gaps")
            if gap_report.gaps:
                for item in gap_report.gaps:
                    priority_badge = item.priority.upper()
                    st.markdown(
                        f"- **{item.skill}**: Current {item.current}/5 → Required {item.required}/5 "
                        f"`{priority_badge}` (Gap: -{item.gap})"
                    )
            else:
                st.success("🎉 No skill gaps! You meet or exceed all role requirements.")

    with col_strengths:
        with st.container(border=True):
            st.markdown("#### Core Strengths")
            if gap_report.strengths:
                for strength in gap_report.strengths:
                    st.markdown(f"- ✅ **{strength}**")
            else:
                st.caption("No specific strengths detected yet.")
