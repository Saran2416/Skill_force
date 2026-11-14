"""Prompt text owned by the Skill Analysis agent."""

SYSTEM_PROMPT = (
    "You are a precise skills assessor. Output ONLY JSON matching the schema. Never invent skills the user did "
    "not state or that the projects do not clearly imply. When unsure, choose the lower level."
)

RUBRIC = """Level rubric:
0 = no evidence
1 = heard of it
2 = basic
3 = builds small things
4 = comfortable
5 = expert"""


def stated_skills_prompt(raw_text: str) -> str:
    """Build the user prompt for skills the learner states directly."""

    return (
        "Extract and rate ONLY the skills the learner explicitly states in the profile text below.\n"
        f"{RUBRIC}\n"
        "Use the skill name the learner wrote. Do not add skills that are not actually stated.\n"
        "Return JSON with a 'skills' array of objects containing 'name' and 'level'.\n\n"
        "PROFILE TEXT:\n"
        f"{raw_text.strip()}"
    )


def inferred_skills_prompt(certs: list[str], projects: list[str]) -> str:
    """Build the user prompt for skills implied by certifications and projects."""

    cert_lines = "\n".join(f"- {cert}" for cert in certs) or "- (none)"
    project_lines = "\n".join(f"- {project}" for project in projects) or "- (none)"
    return (
        "Infer only the skills that are clearly implied by the certifications and projects below.\n"
        f"{RUBRIC}\n"
        "Every inferred skill must be capped at level 3. Choose a lower level when the evidence is weak.\n"
        "Do not infer anything from the learner's stated profile text; use only this metadata.\n"
        "Return JSON with a 'skills' array of objects containing 'name' and 'level'.\n\n"
        f"CERTIFICATIONS:\n{cert_lines}\n\nPROJECTS:\n{project_lines}"
    )
