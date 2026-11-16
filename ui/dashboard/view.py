"""Streamlit rendering for the learner dashboard.

Read-only by contract: it never mutates ``state``, never writes
``st.session_state``, never calls an LLM and never touches the network or disk.
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

from .logic import (
    advantages,
    disadvantages,
    known_languages,
    progress,
    required_skills_table,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from contracts.schemas import AppState

_STATUS_COLORS = {"met": "#1a7f37", "gap": "#b7791f", "missing": "#c0392b"}
_GREEN = "#1a7f37"
_RED = "#c0392b"
_AMBER = "#b7791f"


def _badge(confidence: str) -> str:
    """Small colored pill describing where the requirements came from."""

    if confidence == "curated":
        return (
            f"<span style='background:{_GREEN};color:#fff;padding:2px 10px;"
            "border-radius:10px;font-size:0.72rem;font-weight:600;'>Curated</span>"
        )
    return (
        f"<span style='background:{_AMBER};color:#fff;padding:2px 10px;"
        "border-radius:10px;font-size:0.72rem;font-weight:600;'>AI-estimated</span>"
    )


def _chip(label: str) -> str:
    return (
        "<span style='display:inline-block;background:#eef2ff;color:#1f2a6b;"
        "border-radius:12px;padding:2px 10px;margin:0 6px 6px 0;"
        f"font-size:0.8rem;'>{html.escape(label)}</span>"
    )


def _skills_table_html(rows: list[dict]) -> str:
    header = (
        "<tr>"
        "<th style='text-align:left;padding:4px 6px;border-bottom:1px solid #ddd;'>Skill</th>"
        "<th style='text-align:center;padding:4px 6px;border-bottom:1px solid #ddd;'>Required</th>"
        "<th style='text-align:center;padding:4px 6px;border-bottom:1px solid #ddd;'>Current</th>"
        "<th style='text-align:left;padding:4px 6px;border-bottom:1px solid #ddd;'>Priority</th>"
        "<th style='text-align:left;padding:4px 6px;border-bottom:1px solid #ddd;'>Status</th>"
        "</tr>"
    )
    body = []
    for row in rows:
        color = _STATUS_COLORS.get(row["status"], "#555")
        body.append(
            "<tr>"
            f"<td style='padding:4px 6px;'>{html.escape(str(row['skill']))}</td>"
            f"<td style='text-align:center;padding:4px 6px;'>{row['required']}</td>"
            f"<td style='text-align:center;padding:4px 6px;'>{row['current']}</td>"
            f"<td style='padding:4px 6px;'>{html.escape(str(row['priority']))}</td>"
            f"<td style='padding:4px 6px;color:{color};font-weight:600;'>"
            f"{html.escape(str(row['status']))}</td>"
            "</tr>"
        )
    return (
        "<table style='width:100%;border-collapse:collapse;font-size:0.85rem;'>"
        f"{header}{''.join(body)}</table>"
    )


def _bullet_list(items: list[str], color: str) -> str:
    return "".join(
        f"<div style='color:{color};margin:2px 0;'>\u2022 {html.escape(item)}</div>"
        for item in items
    )


def render_dashboard(state: "AppState") -> None:
    """Render the learner dashboard for ``state``. Read-only."""

    import streamlit as st

    st.markdown(
        """
        <style>
          @keyframes sf-pop-in {
            from { opacity: 0; transform: translateY(12px) scale(0.985); }
            to { opacity: 1; transform: translateY(0) scale(1); }
          }
          @keyframes sf-glow {
            0%, 100% { box-shadow: 0 0 0 rgba(96,165,250,0); }
            50% { box-shadow: 0 0 0 6px rgba(96,165,250,0.08); }
          }
          [data-testid="stMetric"] { animation: sf-pop-in 420ms ease both; }
          div[data-testid="stVerticalBlockBorderWrapper"] { animation: sf-pop-in 460ms ease both; }
          [data-testid="stPlotlyChart"] { animation: sf-pop-in 520ms ease both; }
          .sf-next-step-highlight { animation: sf-glow 2.4s ease-in-out infinite; border-radius: 14px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    profile = getattr(state, "profile", None)
    requirements = getattr(state, "requirements", None)

    if requirements is None:
        st.info(
            "Your dashboard is empty. Complete the **Profile** tab to generate "
            "a personalised match analysis."
        )
        return

    st.subheader("Dashboard Overview")
    st.caption("A snapshot of your target, readiness, and next actions.")

    gap = getattr(state, "gap", None)
    prog = progress(state)

    # --- Top row: four metric cards -------------------------------------
    target_role = (getattr(profile, "target_role", "") or "").strip() or "Not set"
    company = requirements.company or "Any company"
    match = f"{gap.match_percent:g}%" if gap is not None else "—"

    col_role, col_company, col_match, col_progress = st.columns(4)
    col_role.metric("Target Role", target_role)
    col_company.metric("Target Company", company)
    col_company.markdown(_badge(requirements.confidence), unsafe_allow_html=True)
    col_match.metric("Match", match)
    col_progress.metric("Roadmap Progress", f"{prog['percent']:g}%")
    if prog["total"]:
        col_progress.caption(f"{prog['done']}/{prog['total']} steps completed")

    st.divider()

    # --- Middle row: languages + required skills ------------------------
    left, right = st.columns(2, gap="large")

    with left:
        st.subheader("Languages You Know")
        languages = known_languages(profile)
        if languages:
            st.markdown(
                "".join(_chip(skill.name) for skill in languages),
                unsafe_allow_html=True,
            )
            for skill in languages:
                st.caption(f"{skill.name} \u2014 level {skill.level}/5")
                st.progress(min(max(skill.level / 5.0, 0.0), 1.0))
        else:
            st.caption("No programming languages yet. Add skills in the Profile tab.")

    with right:
        st.subheader("Required Skills")
        rows = required_skills_table(state)
        if rows:
            st.markdown(_skills_table_html(rows), unsafe_allow_html=True)
        else:
            st.caption("No requirements available yet.")

    st.divider()

    # --- Advantages / disadvantages -------------------------------------
    adv_col, dis_col = st.columns(2, gap="large")

    with adv_col:
        with st.container(border=True):
            st.subheader("Strengths & Advantages")
            strengths = advantages(state)
            if strengths:
                st.markdown(_bullet_list(strengths, _GREEN), unsafe_allow_html=True)
            else:
                st.caption("Save your profile to see personalized strengths.")

    with dis_col:
        with st.container(border=True):
            st.subheader("Gaps & Risks")
            weaknesses = disadvantages(state)
            if weaknesses:
                st.markdown(_bullet_list(weaknesses, _RED), unsafe_allow_html=True)
            else:
                st.caption("Save your profile to see personalized gaps.")

    st.divider()

    # --- Bottom row: next step + score history --------------------------
    bottom_left, bottom_right = st.columns([1, 2], gap="large")

    with bottom_left:
        st.markdown('<div class="sf-next-step-highlight">', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("**Recommended Next Step**")
            if prog["next_step"]:
                st.write(f"Focus on **{prog['next_step']}** to move your roadmap forward.")
            elif prog["total"] == 0:
                st.caption("No roadmap steps yet. Save your profile to generate a plan.")
            else:
                st.success("Roadmap complete. Keep validating skills with assessments.")
        st.markdown("</div>", unsafe_allow_html=True)

    with bottom_right:
        with st.container(border=True):
            st.markdown("**Assessment Scores**")
            scores = list(getattr(state, "scores", None) or [])
            if scores:
                from plotly import graph_objects as go

                figure = go.Figure(
                    go.Bar(
                        x=[score.skill for score in scores],
                        y=[score.score_percent for score in scores],
                        marker=dict(color="#60a5fa", line=dict(color="#3b82f6", width=1)),
                        text=[f"{score.score_percent:g}%" for score in scores],
                        textposition="outside",
                    )
                )
                figure.update_layout(
                    height=260,
                    margin=dict(l=10, r=10, t=10, b=10),
                    yaxis_title="Score %",
                    yaxis=dict(range=[0, 110], gridcolor="rgba(148,163,184,0.25)"),
                    xaxis=dict(tickangle=-20),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#94a3b8"),
                    showlegend=False,
                    transition=dict(duration=500, easing="cubic-in-out"),
                )
                st.plotly_chart(figure, use_container_width=True)
            else:
                st.caption("No assessment scores yet. Complete a quiz or simulation to track progress.")


__all__ = ["render_dashboard"]
