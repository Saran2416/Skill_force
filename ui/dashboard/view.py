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

    profile = getattr(state, "profile", None)
    requirements = getattr(state, "requirements", None)

    if requirements is None:
        st.info(
            "Your dashboard is empty. Complete the **Profile** tab to generate "
            "a personalised match analysis."
        )
        return

    st.markdown("#### Dashboard")

    gap = getattr(state, "gap", None)
    prog = progress(state)

    # --- Top row: four metric cards -------------------------------------
    target_role = (getattr(profile, "target_role", "") or "").strip() or "Not set"
    company = requirements.company or "Any"
    match = f"{gap.match_percent:g}%" if gap is not None else "\u2014"

    col_role, col_company, col_match, col_progress = st.columns(4)
    col_role.metric("Target Role", target_role)
    col_company.metric("Target Company", company)
    col_company.markdown(_badge(requirements.confidence), unsafe_allow_html=True)
    col_match.metric("Match %", match)
    col_progress.metric("Roadmap progress %", f"{prog['percent']:g}%")

    # --- Middle row: languages + required skills ------------------------
    left, right = st.columns(2)

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

    # --- Advantages / disadvantages -------------------------------------
    adv_col, dis_col = st.columns(2)

    with adv_col:
        st.subheader("Advantages")
        strengths = advantages(state)
        if strengths:
            st.markdown(_bullet_list(strengths, _GREEN), unsafe_allow_html=True)
        else:
            st.caption("Save your profile to see this")

    with dis_col:
        st.subheader("Disadvantages")
        weaknesses = disadvantages(state)
        if weaknesses:
            st.markdown(_bullet_list(weaknesses, _RED), unsafe_allow_html=True)
        else:
            st.caption("Save your profile to see this")

    # --- Bottom row: next step + score history --------------------------
    bottom_left, bottom_right = st.columns([1, 2])

    with bottom_left:
        with st.container(border=True):
            st.markdown("**Next step**")
            if prog["next_step"]:
                st.write(prog["next_step"])
            elif prog["total"] == 0:
                st.caption("No roadmap steps yet.")
            else:
                st.caption("Roadmap complete \U0001f389")

    with bottom_right:
        st.markdown("**Assessment scores over time**")
        scores = list(getattr(state, "scores", None) or [])
        if scores:
            from plotly import graph_objects as go

            figure = go.Figure(
                go.Bar(
                    x=[score.skill for score in scores],
                    y=[score.score_percent for score in scores],
                    marker_color="#4c6ef5",
                )
            )
            figure.update_layout(
                height=240,
                margin=dict(l=10, r=10, t=10, b=10),
                yaxis_title="Score %",
                showlegend=False,
            )
            st.plotly_chart(figure, use_container_width=True)
        else:
            st.caption("No assessment scores yet.")


__all__ = ["render_dashboard"]
