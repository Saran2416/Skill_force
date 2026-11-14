# SkillPath

SkillPath is a multi-agent learning platform scaffold.

## Ownership table

| Path | Owner |
| --- | --- |
| data/ | Agent 1 |
| storage/ | Agent 1 |
| agents/skill_analyst/ | Agent 2 |
| agents/company_intel/ | Agent 3 |
| agents/career_matcher/ | Agent 4 |
| agents/planner/ | Agent 5 |
| agents/assessor/ | Agent 6 |
| agents/mentor/ | Agent 7 |
| ui/ and app.py, excluding ui/dashboard/ | Agent 8 |
| ui/dashboard/ | Agent 9 |
| contracts/ | Lead |
| requirements.txt | Lead |
| scripts/ | Lead |
| NOTES.md | All |

## Rules

1. Edit only your owned paths.
2. Never edit contracts/, requirements.txt or scripts/.
3. For shared changes, add notes to NOTES.md under your heading.
4. Do not rename public functions.
5. Tests live inside your own folder.
6. Push only your own branch, never main, and never force-push.

## Setup

```bash
python -m venv .venv
. .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m pytest
```
