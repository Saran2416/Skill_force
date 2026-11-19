# SkillForce

SkillForce is a React + FastAPI learning and career-planning application. It compares a learner profile with a target role, recommends next steps, and adjusts the roadmap after assessments.

The frontend is a Vite + React + Tailwind app in `frontend/`; the backend is a FastAPI REST API in `server/` that reuses the existing agent, data, and storage modules.

## Quick start (macOS/Linux)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..

# terminal 1 — API server (mock LLM, demo mode)
USE_MOCK_LLM=1 UI_FIXTURE=1 python -m uvicorn server.app:app --port 8000

# terminal 2 — frontend dev server
cd frontend && npm run dev
```

Open <http://localhost:5173> and click **Continue with demo account**. Windows instructions and full options are below.

## Requirements

- Python 3.10 or later
- Node.js 18 or later
- An LLM API key is optional — mock mode works offline

## Set up the environment

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cd frontend && npm install && cd ..
```

## Run the application

### Development (two processes)

Terminal 1 — API server:

```bash
export USE_MOCK_LLM=1
export UI_FIXTURE=0
python -m uvicorn server.app:app --reload --port 8000
```

Windows PowerShell:

```powershell
$env:USE_MOCK_LLM = "1"
$env:UI_FIXTURE = "0"
python -m uvicorn server.app:app --reload --port 8000
```

Terminal 2 — frontend dev server (proxies `/api` to port 8000):

```bash
cd frontend
npm run dev
```

Open <http://localhost:5173>.

### Production (single process)

```bash
cd frontend && npm run build && cd ..
python -m uvicorn server.app:app --port 8000
```

Open <http://localhost:8000>. FastAPI serves `frontend/dist` with SPA fallback, so no second process is needed.

### Application workflow

1. **Sign in or create an account** on the authentication screen.
2. **Complete your profile** (name, skills, certifications/projects as needed, and target role/company).
3. **Save the profile** to generate a personalized roadmap, including role requirements, skill-gap analysis, recommendations, and next learning steps.
4. Continue using the app to track progress, take assessments, and adapt the roadmap.

### Modes

- **Authenticated mode (`UI_FIXTURE=0`, recommended):** account-based access with persisted user profiles and progress in SQLite.
- **Demo mode (`UI_FIXTURE=1`):** authentication is still required, but the sign-in screen includes **"Continue with demo account"** for quick access to a preloaded sample profile.

### API

The React app talks to a JSON API under `/api` (interactive docs at `/docs` when the server runs):

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/auth/session` | Current session (username or null) |
| POST | `/api/auth/login` `/signup` `/demo` | Authentication (session cookie) |
| POST | `/api/auth/logout` | Clear the session |
| GET | `/api/state` | Full `AppState` + latest explanation |
| GET | `/api/meta` | Role/company/skill/cert dictionaries for the Profile form |
| POST | `/api/profile/save` | Save the profile and (re)generate requirements, gap, and roadmap |
| POST | `/api/assessment/quiz/generate` | Generate a 5-question quiz for a skill |
| POST | `/api/assessment/quiz/submit` | Score a quiz and record the result |
| POST | `/api/assessment/simulate` | Record a simulated score |
| POST | `/api/mentor/chat` | Mentor chat turn (returns the reply) |
| GET | `/api/dashboard` | Dashboard read model (pure logic) |
| GET | `/api/gap/radar` | Radar chart data (current vs. required) |

### Data storage

- Default database path: `storage/skillforce.db`
- Override with `SKILLFORCE_DB_PATH`
- Accounts, profile data, and app state are stored in SQLite.

## Configure a live LLM (optional)

Set `USE_MOCK_LLM=0` and configure:

- `LLM_PROVIDER`: `anthropic` or `openai`
- `LLM_MODEL`: a model name supported by the selected provider
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`: the API key for that provider

```bash
export USE_MOCK_LLM=0
export LLM_PROVIDER=anthropic
export LLM_MODEL="<model-name>"
export ANTHROPIC_API_KEY="<your-api-key>"
python -m uvicorn server.app:app --port 8000
```

Do not commit API keys. `.env.example` lists the supported variables; the application reads them from the process environment.

## Deploy on Vercel

`Dockerfile.vercel` builds the React frontend with Node, then runs the FastAPI server with uvicorn on the port provided by Vercel. The container uses mock LLM responses and sample learner data, so no API keys are needed for the demo.

```bash
npx vercel@65.14.0 login
npx vercel@65.14.0 link
npx vercel@65.14.0 --prod
```

The SQLite database is placed under `/tmp` and is ephemeral; use an external database if learner data must persist across container restarts or instances.

## Run the tests

```bash
USE_MOCK_LLM=1 python -m pytest -q
```

Frontend type-check and build:

```bash
cd frontend && npm run build
```

## Project layout

| Path | Purpose |
| --- | --- |
| `frontend/` | React + Vite + Tailwind application |
| `server/` | FastAPI REST API, session handling, and profile form helpers |
| `agents/` | Skill analysis, company intelligence, career matching, planning, assessment, and mentoring |
| `contracts/` | Shared schemas, sample state, and LLM adapter |
| `data/` | Curated roles, companies, and learning resources |
| `storage/` | SQLite persistence |
| `ui/dashboard/` | Pure dashboard read models |
| `tests/` | Shared contract tests |

## Agent ownership

| Path | Owner |
| --- | --- |
| `data/`, `storage/` | Agent 1 |
| `agents/skill_analyst/` | Agent 2 |
| `agents/company_intel/` | Agent 3 |
| `agents/career_matcher/` | Agent 4 |
| `agents/planner/` | Agent 5 |
| `agents/assessor/` | Agent 6 |
| `agents/mentor/` | Agent 7 |
| `frontend/` and `server/` | Agent 8 |
| `ui/dashboard/` | Agent 9 |
| `NOTES.md` | All agents |
| `contracts/`, `requirements.txt`, `scripts/` | Lead |

When contributing, stay within your owned paths, add tests alongside your component, and do not rename public functions. Coordinate shared-file changes with the project lead and document them in `NOTES.md`. Push only your own branch; do not push `main` or force-push.
