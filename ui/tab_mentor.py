from __future__ import annotations

import streamlit as st
from contracts.schemas import AppState
from ui.events import dispatch_event, explain_app_changes


def render_mentor_tab(state: AppState, user_id: str) -> None:
    """Render the career mentor tab with interactive chat (CHAT events) and latest explain_changes."""
    st.subheader("SkillPath Career Mentor")

    # Latest explain_changes section
    st.markdown("#### 💡 Latest System & Progress Explanation")
    latest_explanation = st.session_state.get("latest_explanation")
    if not latest_explanation:
        latest_explanation = explain_app_changes(state, state)

    with st.container(border=True):
        st.write(latest_explanation)

    st.divider()

    # Chat with Mentor section
    st.markdown("#### 💬 Chat with Mentor")

    # Initialize chat history
    if "mentor_chat_history" not in st.session_state:
        target_role = state.profile.target_role or "your target career"
        target_co = (
            f" at {state.profile.target_company}"
            if state.profile.target_company
            else ""
        )
        st.session_state["mentor_chat_history"] = [
            {
                "role": "assistant",
                "content": (
                    f"Hello {state.profile.name or 'there'}! I am your SkillPath mentor. "
                    f"I'm here to help you navigate your journey toward becoming a **{target_role}{target_co}**. "
                    "Ask me about closing skill gaps, preparing for technical interviews, or prioritizing roadmap tasks!"
                ),
            }
        ]

    # Render previous messages
    for msg in st.session_state["mentor_chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_prompt = st.chat_input("Ask a question about your learning plan, interview rounds, or skills...")
    if user_prompt:
        # Append and display user message
        st.session_state["mentor_chat_history"].append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        try:
            with st.spinner("Mentor is reviewing your profile and formulating advice..."):
                _, explanation = dispatch_event(
                    state,
                    {"type": "CHAT", "message": user_prompt},
                    user_id,
                )
                st.session_state["latest_explanation"] = explanation

                # Craft contextual mentor response
                skills_summary = ", ".join(s.name for s in state.profile.skills[:3]) or "core fundamentals"
                mentor_reply = (
                    f"Thanks for asking about **'{user_prompt}'**. "
                    f"Looking at your profile with experience in {skills_summary} aiming for "
                    f"**{state.profile.target_role or 'your target role'}**, I recommend concentrating on "
                    "the top-priority items in your **Roadmap** tab. Build hands-on projects and test your skills "
                    "in the **Assessment** tab to validate your progress."
                )

                st.session_state["mentor_chat_history"].append({"role": "assistant", "content": mentor_reply})
                with st.chat_message("assistant"):
                    st.markdown(mentor_reply)
        except Exception as exc:
            st.error(f"Failed to communicate with mentor: {exc}")
