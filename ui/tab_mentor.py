from __future__ import annotations

import streamlit as st
from contracts.schemas import AppState
from ui.events import dispatch_event


def render_mentor_tab(state: AppState, user_id: str) -> None:
    """Render the career mentor tab with interactive chat (CHAT events) and latest explain_changes."""
    st.subheader("SkillForce Career Mentor")
    st.caption("Get guidance tailored to your profile, target role, and latest progress.")

    # Latest explain_changes section
    st.markdown("#### 💡 Latest System & Progress Explanation")
    latest_explanation = st.session_state.get("latest_explanation")
    if not latest_explanation:
        latest_explanation = "Save your profile or complete an assessment to see plan changes here."

    with st.container(border=True):
        st.write(latest_explanation)

    st.divider()

    # Chat with Mentor section
    st.markdown("#### 💬 Chat with Mentor")

    target_role = state.profile.target_role or "your target career"
    target_company = state.profile.target_company
    target_co = f" at {target_company}" if target_company else ""
    welcome_message = (
        f"Hello {state.profile.name or 'there'}! I am your SkillForce mentor. "
        f"I'm here to help you navigate your journey toward becoming a **{target_role}{target_co}**. "
        "Ask me about closing skill gaps, preparing for technical interviews, or prioritizing roadmap tasks!"
    )
    target_key = (state.profile.target_role, target_company)
    if "mentor_chat_history" not in st.session_state:
        st.session_state["mentor_chat_history"] = [
            {"role": "assistant", "content": welcome_message}
        ]
        st.session_state["mentor_chat_target"] = target_key
    else:
        chat_history = st.session_state["mentor_chat_history"]
        if (
            chat_history
            and chat_history[0].get("role") == "assistant"
            and (
                "I am your SkillForce mentor." in chat_history[0].get("content", "")
                or "I am your SkillPath mentor." in chat_history[0].get("content", "")
            )
            and chat_history[0]["content"] != welcome_message
        ):
            chat_history[0]["content"] = welcome_message
        st.session_state["mentor_chat_target"] = target_key

    # Render previous messages
    for msg in st.session_state["mentor_chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat controls
    col_input_hint, col_clear = st.columns([4, 1])
    with col_clear:
        if st.button("Clear chat", use_container_width=True):
            st.session_state.pop("mentor_chat_history", None)
            st.session_state.pop("mentor_chat_target", None)
            st.rerun()

    # Chat input
    user_prompt = st.chat_input("Ask a question about your learning plan, interview rounds, or skills...")
    if user_prompt:
        # Append and display user message
        st.session_state["mentor_chat_history"].append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        try:
            with st.spinner("Mentor is reviewing your profile and formulating advice..."):
                updated_state, explanation = dispatch_event(
                    state,
                    {"type": "CHAT", "message": user_prompt},
                    user_id,
                )
                st.session_state.state = updated_state
                if explanation != "No target, skill, readiness, or roadmap changes.":
                    st.session_state["latest_explanation"] = explanation

                latest_entry = updated_state.log[-1] if updated_state.log else None
                if latest_entry is not None and latest_entry.action in {
                    "chat_response",
                    "chat_unavailable",
                }:
                    mentor_reply = latest_entry.reason
                    if latest_entry.action == "chat_unavailable":
                        st.error(latest_entry.reason)
                else:
                    mentor_reply = "The mentor could not provide a response. Check the activity log for details."

                st.session_state["mentor_chat_history"].append({"role": "assistant", "content": mentor_reply})
                with st.chat_message("assistant"):
                    st.markdown(mentor_reply)
                st.rerun()
        except Exception as exc:
            st.error(f"Failed to communicate with mentor: {exc}")
