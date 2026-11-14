from __future__ import annotations

import re
import streamlit as st
from contracts.schemas import AppState, Skill
from data.loader import _company_records, _role_records
from ui.events import dispatch_event


def parse_skills_input(text: str, existing_skills: list[Skill] | None = None) -> list[Skill]:
    """Parse free-text skill input into a list of Skill objects.

    Accepts newline- or comma-separated entries such as:
      Python: 3
      SQL: 4
      HTML
      React (3)
    """
    existing_map = {
        s.name.strip().casefold(): s.level for s in (existing_skills or [])
    }
    skills: list[Skill] = []
    seen: set[str] = set()

    # Split by newlines or commas
    tokens = re.split(r"[\n,]+", text)
    for raw in tokens:
        token = raw.strip()
        if not token:
            continue

        # Look for "Name: Level" or "Name (Level)" or bare "Name"
        match = re.match(r"^([^:()]+?)(?:[:(]\s*(\d+)\s*\)?)?$", token)
        if not match:
            continue

        name = match.group(1).strip()
        level_str = match.group(2)
        norm_key = name.casefold()

        if not name or norm_key in seen:
            continue
        seen.add(norm_key)

        if level_str is not None:
            level = max(0, min(5, int(level_str)))
        elif norm_key in existing_map:
            level = existing_map[norm_key]
        else:
            level = 3

        skills.append(Skill(name=name, level=level, source="user"))

    return skills


def parse_list_input(text: str) -> list[str]:
    """Parse newline- or comma-separated text into a clean list of strings."""
    items: list[str] = []
    seen: set[str] = set()
    for token in re.split(r"[\n,]+", text):
        clean = token.strip()
        if clean and clean.casefold() not in seen:
            seen.add(clean.casefold())
            items.append(clean)
    return items


def render_profile_tab(state: AppState, user_id: str) -> None:
    """Render the Profile configuration tab."""
    st.subheader("Learner Profile")

    # Name input
    name = st.text_input(
        "Full Name",
        value=state.profile.name or user_id,
        help="Learner or candidate name.",
    )

    # Free-text skills
    default_skills = "\n".join(
        f"{s.name}: {s.level}" for s in state.profile.skills
    )
    skills_text = st.text_area(
        "Skills",
        value=default_skills,
        help="Enter skills with optional levels (0-5), e.g., 'Python: 3' or 'SQL: 4'. One per line or comma-separated.",
        height=120,
    )

    # Certs input
    default_certs = "\n".join(state.profile.certs)
    certs_text = st.text_area(
        "Certifications",
        value=default_certs,
        help="Enter certifications, one per line or comma-separated.",
        height=90,
    )

    # Projects input
    default_projects = "\n".join(state.profile.projects)
    projects_text = st.text_area(
        "Key Projects",
        value=default_projects,
        help="Enter key projects, one per line or comma-separated.",
        height=90,
    )

    # Target Role dropdown
    curated_roles = [record["role"] for record in _role_records()]
    current_role = state.profile.target_role or (curated_roles[0] if curated_roles else "")
    if current_role and current_role not in curated_roles:
        role_options = [current_role] + curated_roles
    else:
        role_options = curated_roles

    role_index = (
        role_options.index(current_role)
        if current_role in role_options
        else 0
    )
    target_role = st.selectbox(
        "Target Role",
        options=role_options,
        index=role_index,
        help="Select the target career path.",
    )

    # Target Company dropdown (curated companies + Other...)
    curated_companies = [record["company"] for record in _company_records()]
    company_options = curated_companies + ["Other..."]

    current_company = state.profile.target_company
    if current_company in curated_companies:
        company_index = curated_companies.index(current_company)
        custom_company_val = ""
    elif current_company:
        company_index = len(curated_companies)  # "Other..."
        custom_company_val = current_company
    else:
        company_index = 0
        custom_company_val = ""

    selected_company_choice = st.selectbox(
        "Target Company",
        options=company_options,
        index=company_index,
        help="Select the company you are targeting or choose 'Other...'.",
    )

    if selected_company_choice == "Other...":
        custom_company_input = st.text_input(
            "Specify Company Name",
            value=custom_company_val,
            placeholder="e.g. Acme Corp",
        )
        final_company = custom_company_input.strip() or None
    else:
        final_company = selected_company_choice

    # Save button
    if st.button("Save Profile", type="primary", use_container_width=True):
        try:
            with st.spinner("Saving profile and updating target..."):
                old_role = state.profile.target_role
                old_company = state.profile.target_company

                # Update profile fields
                state.profile.name = name.strip() or user_id
                state.profile.skills = parse_skills_input(
                    skills_text, existing_skills=state.profile.skills
                )
                state.profile.certs = parse_list_input(certs_text)
                state.profile.projects = parse_list_input(projects_text)
                state.profile.target_role = target_role
                state.profile.target_company = final_company

                # Dispatch PROFILE_SAVED event
                _, explanation = dispatch_event(
                    state, {"type": "PROFILE_SAVED"}, user_id
                )
                st.session_state["latest_explanation"] = explanation

                # Dispatch TARGET_CHANGED if role or company changed
                if target_role != old_role or final_company != old_company:
                    _, explanation = dispatch_event(
                        state,
                        {
                            "type": "TARGET_CHANGED",
                            "role": target_role,
                            "company": final_company,
                        },
                        user_id,
                    )
                    st.session_state["latest_explanation"] = explanation

                st.toast("Profile saved successfully!", icon="✅")
                st.success("Profile updated and persisted successfully.")
        except Exception as exc:
            st.error(f"Failed to save profile: {exc}")
