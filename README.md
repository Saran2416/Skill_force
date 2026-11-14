# SkillPath

SkillPath is a Streamlit learning and career-planning application. It compares a learner profile with a target role, recommends next steps, and adjusts the roadmap after assessments.

## Requirements

- Python 3.10 or later
- `pip`
- An LLM API key is optional. Mock mode works offline.

Run commands from the project root.

## Set up the environment

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell prevents virtual-environment activation, run the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run the application

Mock mode uses deterministic local responses and does not require API credentials.

### Windows PowerShell

```powershell
$env:USE_MOCK_LLM = "1"
$env:UI_FIXTURE = "1"
python -m streamlit run app.py
```

### macOS or Linux

```bash
export USE_MOCK_LLM=1
export UI_FIXTURE=1
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, usually <http://localhost:8501>.

The app starts with a sample learner when `UI_FIXTURE=1` (the default). Set `UI_FIXTURE=0` to load the learner state from SQLite instead. The default database path is `storage/skillpath.db`; set `SKILLPATH_DB_PATH` to use another location. Profile and event updates are saved to the database.

## Configure a live LLM (optional)

To use live model responses, set `USE_MOCK_LLM=0` and configure:

- `LLM_PROVIDER`: `anthropic` or `openai`
- `LLM_MODEL`: a model name supported by the selected provider
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`: the API key for that provider

For example, in PowerShell:

```powershell
$env:USE_MOCK_LLM = "0"
$env:LLM_PROVIDER = "anthropic"
$env:LLM_MODEL = "<model-name>"
$env:ANTHROPIC_API_KEY = "<your-api-key>"
python -m streamlit run app.py
```

For OpenAI, set `LLM_PROVIDER` to `openai` and provide `OPENAI_API_KEY` instead. Do not commit API keys. `.env.example` lists the supported variables; the application reads them from the process environment.

## Deploy on Vercel

Vercel's Python function runtime expects an ASGI/WSGI entrypoint, while this project is a Streamlit server. `Dockerfile.vercel` selects Vercel's container runtime and starts Streamlit on the port provided by Vercel. The container uses mock LLM responses and sample learner data, so no API keys are needed for the demo.

After signing in and linking the repository with the Vercel CLI, deploy from the project root:

```bash
npx vercel@65.14.0 login
npx vercel@65.14.0 link
npx vercel@65.14.0 --prod
```

The container runtime and Vercel WebSocket support are currently in beta. The SQLite database is placed under `/tmp` and is ephemeral; use an external database if learner data must persist across container restarts or instances.

## Run the tests

Mock mode keeps tests independent of external API credentials.

### Windows PowerShell

```powershell
$env:USE_MOCK_LLM = "1"
python -m pytest -q
```

### macOS or Linux

```bash
USE_MOCK_LLM=1 python -m pytest -q
```

## Project layout

| Path | Purpose |
| --- | --- |
| `agents/` | Skill analysis, company intelligence, career matching, planning, assessment, and mentoring |
| `contracts/` | Shared schemas, sample state, and LLM adapter |
| `data/` | Curated roles, companies, and learning resources |
| `storage/` | SQLite persistence |
| `ui/` | Streamlit tabs and dashboard |
| `app.py` | Streamlit application entry point |
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
| `ui/` and `app.py`, excluding `ui/dashboard/` | Agent 8 |
| `ui/dashboard/` | Agent 9 |
| `NOTES.md` | All agents |
| `contracts/`, `requirements.txt`, `scripts/` | Lead |

When contributing, stay within your owned paths, add tests alongside your component, and do not rename public functions. Coordinate shared-file changes with the project lead and document them in `NOTES.md`. Push only your own branch; do not push `main` or force-push.
