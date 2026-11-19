## Agent 1: Data and Storage

Implemented the curated data layer and SQLite persistence. No shared-file changes are requested.

Data contracts for downstream agents:
- `data.get_role(role)` returns `{role, company, summary, skills, requirements, tools, certs, interview_process, confidence, disclaimer}`.
  `skills` and `requirements` are the same list (the alias is for `RoleRequirements.requirements`). Each item is
  `{skill, level_required, priority, prerequisites, note}`.
- `data.get_company_override(company, role)` returns `{company, role, confidence, last_verified, disclaimer}`
  plus any of `raised_skills`, `extra_skills`, `tools`, `certs`, `interview_process`, `typical_projects`.
  `raised_skills` items are `{skill, level_required, reason}`; `extra_skills` items use the same shape as base
  role skills. Unknown company, unknown role, or a missing pair returns `None`.
- `data.get_resources(skill)` returns `list[Resource]`; lookup is case-insensitive and alias-aware. Unknown skills
  return `[]`.
- `storage.load_state(user_id)` / `storage.save_state(user_id, state)` use SQLite and store `AppState.model_dump_json()`.
  New users get `AppState(profile=UserProfile(name=user_id))`. Set `SKILLFORCE_DB_PATH` to override the default
  `storage/skillforce.db` (useful for tests/deployments). One row per `user_id`; saves are upserts.

Curated files: `data/roles.json` (5 roles), `data/companies.json` (6 companies x 5 roles),
`data/resources.json` (2-3 free, verified links per skill). Tests live in `data/test_loader.py` and
`storage/test_db.py`. All 95 resource URLs were checked; the CISA incident-response link was corrected to its
current location.

## Agent 2: Skill Analyst

## Agent 3: Company Intelligence

- Implemented `get_requirements` and `get_recommendations` in `agents/company_intel/agent.py` and prompts/guardrails in `agents/company_intel/prompts.py`.
- `get_requirements`:
  - Curated base requirements loaded via `data.loader.get_role(role)`.
  - When `company` is provided and `get_company_override(company, role)` exists, merges overrides (raised skills, extra skills, tools, certs, interview stages) with `confidence="curated"` and `disclaimer=""`.
  - When `company` is provided without an override, calls `call_llm` to estimate company-specific requirements, merges onto the base, and sets `confidence="ai_estimated"` with the required disclaimer.
  - When `company` is None, returns base role requirements with `confidence="curated"` and `disclaimer=""`.
- `get_recommendations`:
  - Generates 5-8 recommendations tailored to company domain and learner profile across all five categories: portfolio projects, certifications, interview preparation (DSA/aptitude/system design), open source ideas, and networking.
  - Skips certifications and projects the user already has, and excludes skills the user has already mastered from new learning recommendations.
  - Strict guardrails in prompts prevent fabrication of salaries, internal team names, hiring numbers, and deadlines.
  - Provides deterministic offline mocks for all LLM calls.
- Unit and integration tests in `agents/company_intel/test_agent.py` cover monkeypatched unit cases, unknown company resilience, recommendation filters/counts, and real `data.loader` integration. No shared file changes required.

## Agent 4: Career Matcher

- Implemented `compute_gap` and `radar_data` in `agents/career_matcher/agent.py` with case-insensitive
  skill matching, weighted gaps (must=3, good=2, bonus=1), and priority-ordered radar data.
- Duplicate skill entries use the highest level; duplicate requirements produce one gap each but
  strengths are de-duplicated case-insensitively.
- `radar_data` derives labels/current/required from `GapReport.gaps`, because `GapReport` does not
  retain numeric levels for `strengths`; it re-sorts by must > good > bonus while preserving the
  existing gap order within a priority.
- `radar_data` now accepts optional `req` and `skills`; when both are given it charts all required skills (including strengths), otherwise it keeps the gap-only behavior.

## Agent 5: Planner

- Implemented `build_roadmap(gap, req, weak_skills, completed)` in `agents/planner/agent.py`.
- Created `agents/planner/prereqs.py` providing `PREREQUISITES` mapping for core skills across all 5 target roles (Full Stack, Data Analyst, Cybersecurity Analyst, ML Engineer, DevOps Engineer) and cycle-safe topological sorting using Kahn's algorithm.
- Transitive missing prerequisites are automatically scheduled with `target_level=2` before dependent skills.
- Skills listed in `completed` (or satisfied in strengths) are skipped.
- Skills listed in `weak_skills` receive a `status="revision"` step inserted directly before the main step, tailored to foundational sub-topics and tricky edge cases.
- Resources are retrieved strictly from `data.loader.get_resources(skill)` (never invented).
- Each roadmap step calls `call_llm` with `StepPlan` schema and `SYSTEM_PROMPT` to generate a one-line `mini_project` and 3 `practice_tasks`, backed by deterministic offline mocks for `USE_MOCK_LLM=1`.
- Steps are numbered continuously `1..n`, with `est_hours` computed as ~8 hours per level of gap plus 3 hours per revision step.
- Added comprehensive unit and integration tests in `agents/planner/test_agent.py`, including verification with both mock resources and the real `data.loader`.
- No shared files were modified; no dependencies were added.

## Agent 6: Assessor

## Agent 7: Mentor

## Agent 8: UI

- Implemented Streamlit frontend application in `app.py` and modular tabs in `ui/tab_*.py`, with Dashboard placed first:
  0. **Dashboard** (`ui/tab_dashboard.py`): renders `render_dashboard(state)` from `ui.dashboard`.
  1. **Profile** (`ui/tab_profile.py`): candidate name, free-text skills parser, certs, projects, target role selectbox, and target company selectbox (loaded from `data.loader._role_records` / `_company_records` with "Other..." custom text entry). Dispatches `PROFILE_SAVED` and `TARGET_CHANGED` events.
  2. **Requirements** (`ui/tab_requirements.py`): role requirements breakdown, "Curated" (green) / "AI-estimated" (amber) confidence pill, disclaimer callout, interview stages, required tools, certs, and additional recommendations.
  3. **Gap** (`ui/tab_gap.py`): match percentage metric and Plotly radar chart via `radar_data(state.gap, state.requirements, state.profile.skills)`, plus key gap items and core strengths.
  4. **Roadmap** (`ui/tab_roadmap.py`): ordered steps with target levels, clickable markdown resource links, mini-projects, practice task checklists, and status badges with warning callouts highlighting revision steps.
  5. **Assessment** (`ui/tab_assessment.py`): interactive 5-question quiz with option radio buttons scored via `generate_quiz` and `score_quiz`, score simulation slider (0-100%) via `simulate_score`, `QUIZ_SUBMITTED` event dispatch, score history, and `explain_changes` feedback.
  6. **Mentor** (`ui/tab_mentor.py`): chat UI supporting interactive conversation (`CHAT` events) and display of latest `explain_changes` progress summary.
- Persistent sidebar: displays live Agent Activity Log ordered newest first with timestamps, agent badges, actions, and rationale.
- State & events (`ui/events.py`): state persisted to SQLite with `storage.db.save_state` on every event; supports `UI_FIXTURE=1` fixture execution for unmerged agents (company_intel, planner, mentor).
- Automated tests in `ui/test_smoke.py`: 11 tests using `streamlit.testing.v1.AppTest` verifying clean startup, all 7 tabs, sidebar logs, profile save, score simulation, and mentor chat.

## Agent 9: Dashboard

Implemented `render_dashboard(state)` in `ui/dashboard/view.py` with pure logic split into
`ui/dashboard/logic.py` and the language set in `ui/dashboard/languages.py`. Imports are limited to
`contracts.schemas` / `contracts.sample` plus the dashboard's own modules; the view is read-only and
makes no LLM/network/disk calls and writes no `st.session_state`. No shared-file changes are required,
so there are no requests for the Lead.

## Lead

No ambiguities were encountered; the simplest scaffold implementation was selected.

## Lead: Streamlit → React migration

The frontend was fully migrated from Streamlit to React; `app.py`, `ui/tab_*.py`,
`ui/test_smoke.py`, `ui/events.py`, `ui/dashboard/view.py` (and `.streamlit/`) were deleted.

- **`server/`** (new): FastAPI REST API. `server/app.py` exposes auth (`/api/auth/*`),
  state/meta reads, `/api/profile/save`, assessment (`quiz/generate`, `quiz/submit`,
  `simulate`), `/api/mentor/chat`, `/api/dashboard`, and `/api/gap/radar`. Sessions are
  opaque cookie tokens backed by an in-memory table; `SKILLFORCE_AUTH_USER` still works as
  a stateless auto-auth bypass for automation. It also serves `frontend/dist` with SPA
  fallback in production.
- **Moved (behaviour unchanged):** `ui/events.py` → `server/events.py`;
  profile parsing helpers (`parse_skills_input`, `parse_list_input`, dictionaries) →
  `server/profile.py`. The `ui/dashboard/` pure read models (`logic.py`, `languages.py`)
  are kept and consumed by `/api/dashboard`.
- **`frontend/`** (new): Vite + React 19 + TypeScript + Tailwind v4. All seven tabs
  (Dashboard, Profile, Requirements, Gap, Roadmap, Assessment, Mentor), the auth screen,
  sidebar activity log, and the dark/light theme were ported 1:1; the Plotly radar/bar
  charts became Recharts.
- **Tests:** `ui/test_smoke.py` was replaced by `server/test_api.py` (18 API tests).
  `requirements.txt` now lists `fastapi`/`uvicorn` instead of `streamlit`/`plotly`;
  `Dockerfile.vercel` is a multi-stage Node build + uvicorn runtime.
- **Ownership:** `frontend/` and `server/` are assigned to Agent 8 (`CODEOWNERS`,
  `scripts/check_ownership.py`); Agent 9 keeps `ui/dashboard/`.

