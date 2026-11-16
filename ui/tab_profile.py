from __future__ import annotations

import json
import re
from pathlib import Path
import streamlit as st
from contracts.schemas import AppState, Skill
from data.loader import _company_records, _role_records
from ui.events import dispatch_event


_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_skill_dictionary() -> list[str]:
    skills: set[str] = set()
    try:
        resources = json.loads((_DATA_DIR / "resources.json").read_text(encoding="utf-8"))
        skills.update((resources.get("skills") or {}).keys())
    except Exception:
        pass
    try:
        roles = json.loads((_DATA_DIR / "roles.json").read_text(encoding="utf-8"))
        for role in roles.get("roles", []):
            for item in role.get("skills", role.get("requirements", [])):
                name = item.get("skill") or item.get("name")
                if name:
                    skills.add(str(name))
    except Exception:
        pass
    if not skills:
        skills.update(
            [
                "Python",
                "SQL",
                "JavaScript",
                "HTML",
                "CSS",
                "React",
                "Node.js",
                "Git",
                "REST APIs",
                "Pandas",
                "Spreadsheets",
                "Data Visualization",
                "Statistics",
                "Machine Learning",
                "Docker",
                "Linux",
            ]
        )
    return sorted(skills, key=lambda s: s.lower())


def _load_cert_dictionary() -> list[str]:
    certs: set[str] = set()
    try:
        roles = json.loads((_DATA_DIR / "roles.json").read_text(encoding="utf-8"))
        for role in roles.get("roles", []):
            for cert in role.get("certs", []):
                if cert:
                    certs.add(str(cert))
    except Exception:
        pass
    certs.update(
        [
            "AWS Certified Cloud Practitioner",
            "Microsoft Certified: Azure Fundamentals",
            "Google Data Analytics Professional Certificate",
            "CompTIA Security+",
            "CompTIA Network+",
            "Certified Kubernetes Administrator (CKA)",
        ]
    )
    return sorted(certs, key=lambda s: s.lower())


KNOWN_SKILLS = _load_skill_dictionary()
KNOWN_CERTS = _load_cert_dictionary()


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


def _is_fresh_profile(state: AppState, user_id: str) -> bool:
    profile = state.profile
    name = (profile.name or "").strip()
    has_meaningful_data = bool(
        profile.skills
        or profile.certs
        or profile.projects
        or (profile.target_role or "").strip()
        or profile.target_company
        or state.requirements
        or state.gap
        or state.roadmap
        or state.scores
    )
    # Treat newly created/default profiles as blank so users fill details themselves.
    return not has_meaningful_data and (not name or name == user_id)


def render_profile_tab(state: AppState, user_id: str) -> None:
    """Render the Profile configuration tab."""
    st.subheader("Learner Profile")
    st.caption("Fill in your details to generate a personalized roadmap tailored to your goals.")

    fresh_profile = _is_fresh_profile(state, user_id)

    with st.container(border=True):
        st.markdown("#### Personal Details")
        name = st.text_input(
            "Full Name",
            value="" if fresh_profile else (state.profile.name or ""),
            placeholder="Enter your full name",
            help="Learner or candidate name.",
        )

    with st.container(border=True):
        st.markdown("#### Skills & Experience")
        st.caption("Select skills and proficiency levels from the dictionary, and add any custom skills if needed.")

        existing_skill_map = {
            s.name.strip().casefold(): s
            for s in ([] if fresh_profile else state.profile.skills)
        }
        existing_selected = [
            name for name in KNOWN_SKILLS if name.strip().casefold() in existing_skill_map
        ]
        custom_existing_skills = [
            s for s in ([] if fresh_profile else state.profile.skills)
            if s.name.strip().casefold() not in {k.strip().casefold() for k in KNOWN_SKILLS}
        ]

        selected_skills = st.multiselect(
            "Select skills",
            options=KNOWN_SKILLS,
            default=existing_selected,
            placeholder="Choose skills from the list",
            help="Pick your skills from the predefined dictionary.",
        )

        selected_skill_levels: dict[str, int] = {}
        if selected_skills:
            st.markdown("**Skill levels**")
            level_options = [0, 1, 2, 3, 4, 5]
            for i in range(0, len(selected_skills), 2):
                cols = st.columns(2, gap="large")
                for j, col in enumerate(cols):
                    idx = i + j
                    if idx >= len(selected_skills):
                        continue
                    skill_name = selected_skills[idx]
                    prev = existing_skill_map.get(skill_name.strip().casefold())
                    default_level = prev.level if prev is not None else 3
                    with col:
                        selected_skill_levels[skill_name] = st.selectbox(
                            f"{skill_name} level",
                            options=level_options,
                            index=level_options.index(default_level) if default_level in level_options else 3,
                            key=f"skill_level_{skill_name}",
                            help="0 = none, 5 = expert",
                        )

        default_custom_skills = "" if fresh_profile else "\n".join(
            f"{s.name}: {s.level}" for s in custom_existing_skills
        )
        custom_skills_text = st.text_area(
            "Additional/custom skills",
            value=default_custom_skills,
            help="Add skills not in the dictionary (one per line or comma-separated), e.g. 'Figma: 2'.",
            height=110,
            placeholder="Figma: 2\nPublic Speaking: 4",
        )

        col_certs, col_projects = st.columns(2, gap="large")
        with col_certs:
            existing_certs = [] if fresh_profile else list(state.profile.certs)
            existing_known_certs = [c for c in KNOWN_CERTS if c in existing_certs]
            custom_existing_certs = [c for c in existing_certs if c not in set(KNOWN_CERTS)]
            selected_certs = st.multiselect(
                "Select certifications",
                options=KNOWN_CERTS,
                default=existing_known_certs,
                placeholder="Choose certifications from the list",
                help="Pick certifications from the predefined dictionary.",
            )
            custom_certs_text = st.text_area(
                "Additional/custom certifications",
                value="" if fresh_profile else "\n".join(custom_existing_certs),
                help="Add certifications not in the dictionary, one per line or comma-separated.",
                height=100,
                placeholder="Scrum Master (CSM)\nCompany-specific certification",
            )
        with col_projects:
            default_projects = "" if fresh_profile else "\n".join(state.profile.projects)
            projects_text = st.text_area(
                "Key Projects",
                value=default_projects,
                help="Enter key projects, one per line or comma-separated.",
                height=228,
                placeholder="Personal portfolio website\nSales dashboard in Excel",
            )

    with st.container(border=True):
        st.markdown("#### Career Target")
        col_role, col_company = st.columns(2, gap="large")

        # Target Role dropdown
        curated_roles = [record["role"] for record in _role_records()]
        current_role = "" if fresh_profile else (state.profile.target_role or "")
        if current_role and current_role not in curated_roles:
            role_options = [current_role] + curated_roles
        else:
            role_options = curated_roles

        with col_role:
            role_index = role_options.index(current_role) if current_role in role_options else None
            try:
                target_role = st.selectbox(
                    "Target Role",
                    options=role_options,
                    index=role_index,
                    placeholder="Select a target role",
                    help="Select the target career path.",
                )
            except TypeError:
                # Fallback for older Streamlit versions without placeholder/index=None support.
                fallback_index = role_index if role_index is not None else 0
                target_role = st.selectbox(
                    "Target Role",
                    options=role_options,
                    index=fallback_index if role_options else 0,
                    help="Select the target career path.",
                )

        # Target Company dropdown (curated companies + Other...)
        curated_companies = [record["company"] for record in _company_records()]
        company_options = curated_companies + ["Other..."]
        current_company = None if fresh_profile else state.profile.target_company

        if current_company in curated_companies:
            company_index = curated_companies.index(current_company)
            custom_company_val = ""
            selected_company_default = current_company
        elif current_company:
            company_index = len(curated_companies)  # "Other..."
            custom_company_val = current_company
            selected_company_default = "Other..."
        else:
            company_index = None
            custom_company_val = ""
            selected_company_default = None

        with col_company:
            try:
                selected_company_choice = st.selectbox(
                    "Target Company",
                    options=company_options,
                    index=company_index,
                    placeholder="Select a target company",
                    help="Select the company you are targeting or choose 'Other...'.",
                )
            except TypeError:
                fallback_index = company_index if company_index is not None else 0
                selected_company_choice = st.selectbox(
                    "Target Company",
                    options=company_options,
                    index=fallback_index if company_options else 0,
                    help="Select the company you are targeting or choose 'Other...'.",
                )

        if selected_company_choice == "Other...":
            custom_company_input = st.text_input(
                "Specify Company Name",
                value="" if fresh_profile else custom_company_val,
                placeholder="e.g. Acme Corp",
            )
            final_company = custom_company_input.strip() or None
        else:
            final_company = selected_company_choice if selected_company_choice else None

        if not target_role:
            st.warning("Select a target role to generate your personalized roadmap.")

    st.divider()
    # Save button
    if st.button("Save Profile", type="primary", use_container_width=True):
        cleaned_name = name.strip()
        cleaned_target_role = (target_role or "").strip()

        selected_skill_objects = [
            Skill(
                name=skill_name,
                level=int(selected_skill_levels.get(skill_name, 3)),
                source="user",
            )
            for skill_name in (selected_skills or [])
        ]
        parsed_custom_skill_objects = parse_skills_input(
            custom_skills_text, existing_skills=state.profile.skills
        )
        merged_skills: list[Skill] = []
        seen_skills: set[str] = set()
        for skill in [*selected_skill_objects, *parsed_custom_skill_objects]:
            key = skill.name.strip().casefold()
            if not key or key in seen_skills:
                continue
            seen_skills.add(key)
            merged_skills.append(skill)

        selected_cert_list = list(selected_certs or [])
        parsed_custom_certs = parse_list_input(custom_certs_text)
        merged_certs: list[str] = []
        seen_certs: set[str] = set()
        for cert in [*selected_cert_list, *parsed_custom_certs]:
            clean = str(cert).strip()
            key = clean.casefold()
            if not clean or key in seen_certs:
                continue
            seen_certs.add(key)
            merged_certs.append(clean)

        if not cleaned_name:
            st.error("Please enter your full name.")
            return
        if not cleaned_target_role:
            st.error("Please select a target role to generate your personalized roadmap.")
            return
        if not merged_skills:
            st.error("Please select or add at least one skill so we can personalize your roadmap.")
            return

        try:
            with st.spinner("Saving profile and generating your personalized roadmap..."):
                old_role = state.profile.target_role
                old_company = state.profile.target_company
                target_changed = (
                    cleaned_target_role != old_role or final_company != old_company
                )

                updated_profile = state.model_copy(deep=True)
                updated_profile.profile.name = cleaned_name
                updated_profile.profile.skills = merged_skills
                updated_profile.profile.certs = merged_certs
                updated_profile.profile.projects = parse_list_input(projects_text)
                updated_profile.profile.target_role = cleaned_target_role
                updated_profile.profile.target_company = final_company

                if target_changed:
                    event = {
                        "type": "TARGET_CHANGED",
                        "role": cleaned_target_role,
                        "company": final_company,
                    }
                else:
                    event = {"type": "PROFILE_SAVED"}

                updated_state, explanation = dispatch_event(
                    updated_profile,
                    event,
                    user_id,
                    previous_state=state,
                )
                st.session_state.state = updated_state
                st.session_state["latest_explanation"] = explanation

                if updated_state.log and updated_state.log[-1].action == "agent_failed":
                    st.error(updated_state.log[-1].reason)
                else:
                    st.toast("Profile saved and personalized roadmap generated!", icon="✅")
                    st.success("Profile saved successfully. Your personalized roadmap is ready.")
                st.rerun()
        except Exception as exc:
            st.error(f"Failed to save profile: {exc}")
