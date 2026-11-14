from __future__ import annotations

import streamlit as st
from agents.assessor import generate_quiz, score_quiz, simulate_score
from contracts.schemas import AppState, Quiz, ScoreResult
from ui.events import dispatch_event


def render_assessment_tab(state: AppState, user_id: str) -> None:
    """Render the skill assessment tab with interactive quiz, score simulation, and mentor feedback."""
    st.subheader("Skill Assessment & Verification")

    # Determine skills available for assessment
    candidate_skills: list[str] = []
    if state.profile and state.profile.skills:
        candidate_skills.extend(s.name for s in state.profile.skills)
    if state.requirements and state.requirements.requirements:
        candidate_skills.extend(r.skill for r in state.requirements.requirements)
    if state.roadmap and state.roadmap.steps:
        candidate_skills.extend(s.skill for s in state.roadmap.steps)

    # Unique skills preserving order
    unique_skills = list(dict.fromkeys(s.strip() for s in candidate_skills if s.strip()))
    if not unique_skills:
        unique_skills = ["Python", "SQL", "JavaScript", "HTML"]

    col_skill, col_curr = st.columns([2, 1])
    with col_skill:
        selected_skill = st.selectbox(
            "Select Skill to Assess",
            options=unique_skills,
            help="Choose a skill to test or simulate.",
        )

    # Current level lookup
    current_level = 0
    if state.profile and state.profile.skills:
        for s in state.profile.skills:
            if s.name.strip().casefold() == selected_skill.strip().casefold():
                current_level = s.level
                break

    with col_curr:
        st.metric("Current Level", f"{current_level}/5")

    st.divider()

    # Two column layout: Take Quiz vs Simulate Score
    col_quiz, col_sim = st.columns(2)

    # --- Mode 1: Interactive Quiz ---
    with col_quiz:
        st.markdown("#### 📝 Take Live Quiz")
        st.caption("Generate a tailored 5-question multiple choice assessment.")

        if st.button("Generate Quiz", key="btn_gen_quiz", use_container_width=True):
            try:
                with st.spinner(f"Generating quiz for {selected_skill}..."):
                    quiz = generate_quiz(selected_skill, max(1, current_level))
                    st.session_state["current_quiz"] = quiz
                    st.session_state["active_quiz_skill"] = selected_skill
            except Exception as exc:
                st.error(f"Failed to generate quiz: {exc}")

    # --- Mode 2: Simulate Score ---
    with col_sim:
        st.markdown("#### 🎚️ Simulate Score")
        st.caption("Simulate an assessment outcome to test roadmap and gap impact.")

        sim_score = st.slider(
            "Simulated Score %",
            min_value=0,
            max_value=100,
            value=75,
            step=5,
            help="Simulate a test score percentage.",
        )

        if st.button("Submit Simulated Score", key="btn_sim_submit", use_container_width=True):
            try:
                with st.spinner("Calculating simulated score and updating roadmap..."):
                    result: ScoreResult = simulate_score(
                        selected_skill, sim_score, current_level
                    )
                    _, explanation = dispatch_event(
                        state,
                        {"type": "QUIZ_SUBMITTED", "result": result},
                        user_id,
                    )
                    st.session_state["latest_explanation"] = explanation
                    st.session_state["last_assessment_result"] = result
                    st.toast(
                        f"Simulated score recorded: {result.score_percent:.0f}%!",
                        icon="🎯",
                    )
            except Exception as exc:
                st.error(f"Failed to simulate score: {exc}")

    # Active Quiz rendering
    active_quiz: Quiz | None = st.session_state.get("current_quiz")
    if active_quiz is not None and getattr(active_quiz, "questions", None):
        st.divider()
        st.markdown(f"### Assessment for **{active_quiz.skill}**")
        answers: list[int] = []

        with st.form("quiz_form"):
            for idx, q in enumerate(active_quiz.questions, 1):
                st.markdown(f"**Question {idx}: {q.q}**")
                choice = st.radio(
                    f"Choose answer for Q{idx}:",
                    options=[0, 1, 2, 3],
                    format_func=lambda i, options=q.options: options[i],
                    key=f"q_choice_{q.id}",
                )
                answers.append(choice)

            submit_quiz = st.form_submit_button("Submit Quiz Answers", type="primary")

        if submit_quiz:
            try:
                with st.spinner("Scoring answers and updating profile..."):
                    scored_result: ScoreResult = score_quiz(
                        active_quiz, answers, current_level
                    )
                    _, explanation = dispatch_event(
                        state,
                        {"type": "QUIZ_SUBMITTED", "result": scored_result},
                        user_id,
                    )
                    st.session_state["latest_explanation"] = explanation
                    st.session_state["last_assessment_result"] = scored_result
                    st.session_state["current_quiz"] = None  # Clear quiz
                    st.toast(
                        f"Quiz submitted! Score: {scored_result.score_percent:.1f}%",
                        icon="✅",
                    )
                    st.rerun()
            except Exception as exc:
                st.error(f"Failed to submit quiz: {exc}")

    # Display Latest Result and Explain Changes output
    last_res: ScoreResult | None = st.session_state.get("last_assessment_result")
    explanation_text: str | None = st.session_state.get("latest_explanation")

    if last_res is not None or explanation_text:
        st.divider()
        st.markdown("### Latest Assessment Feedback")

        if last_res is not None:
            col_res1, col_res2, col_res3 = st.columns(3)
            col_res1.metric("Score", f"{last_res.score_percent:g}%")
            col_res2.metric("Updated Skill Level", f"{last_res.new_level}/5")
            flag = "⚠️ Weak (Needs Revision)" if last_res.weak else "✅ Proficient"
            col_res3.metric("Status", flag)

        if explanation_text:
            st.info(f"**Mentor Insights & System Changes:**\n\n{explanation_text}")

    # Score History
    if state.scores:
        st.divider()
        st.markdown("#### Assessment History")
        history_table = [
            {
                "Skill": score.skill,
                "Score %": f"{score.score_percent:g}%",
                "Assigned Level": f"{score.new_level}/5",
                "Weak Area": "Yes" if score.weak else "No",
            }
            for score in reversed(state.scores)
        ]
        st.table(history_table)
