SYSTEM_PROMPT = (
    "You are a supportive but honest learning mentor. Use only the learner's state JSON provided. "
    "Be concise, explain WHY the plan changed, and give exactly one next action."
)


def build_chat_prompt(state_json: str, message: str) -> str:
    """Build a chat prompt using only the supplied state and learner message."""
    return (
        f"Learner state JSON:\n{state_json}\n\n"
        f"Learner message:\n{message}\n\n"
        "Return a concise response and exactly one concrete next action. "
        "Put the action in the next_action field, not in the response field."
    )


__all__ = ["SYSTEM_PROMPT", "build_chat_prompt"]
