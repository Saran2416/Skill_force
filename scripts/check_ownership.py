from __future__ import annotations

import subprocess
import sys

OWNERSHIP = {
    "agent1": ["data/", "storage/"],
    "agent2": ["agents/skill_analyst/"],
    "agent3": ["agents/company_intel/"],
    "agent4": ["agents/career_matcher/"],
    "agent5": ["agents/planner/"],
    "agent6": ["agents/assessor/"],
    "agent7": ["agents/mentor/"],
    "agent8": ["ui/", "app.py"],
    "agent9": ["ui/dashboard/"],
}


def _matches(path: str, rule: str) -> bool:
    normalized = path.strip().replace("\\", "/")
    if rule.endswith("/"):
        return normalized == rule[:-1] or normalized.startswith(rule)
    return normalized == rule or normalized.startswith(f"{rule}/")


def main() -> int:
    agent = sys.argv[1] if len(sys.argv) > 1 else ""
    if agent not in OWNERSHIP:
        print(f"Unknown agent: {agent}")
        return 1

    diff = subprocess.run(
        ["git", "diff", "--name-only", "main...HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if diff.returncode not in {0, 1}:
        print(diff.stderr.strip() or "git diff failed")
        return diff.returncode

    changed = [line.strip() for line in diff.stdout.splitlines() if line.strip()]
    violations = []
    for file_path in changed:
        if file_path.startswith("NOTES.md"):
            continue
        if file_path.startswith(".github/CODEOWNERS"):
            continue
        if file_path.startswith(".gitignore"):
            continue
        if file_path.startswith("requirements.txt"):
            continue
        if file_path.startswith("scripts/") and file_path != "scripts/check_ownership.py":
            continue
        if file_path.startswith("contracts/"):
            continue
        if file_path.startswith("ui/dashboard/") and agent != "agent9":
            violations.append(file_path)
            continue
        if file_path.startswith("ui/dashboard/") and agent == "agent9":
            continue
        if file_path.startswith("ui/") and agent == "agent8":
            if not file_path.startswith("ui/dashboard/"):
                continue
        if file_path == "app.py" and agent != "agent8":
            violations.append(file_path)
            continue
        if any(_matches(file_path, rule) for rule in OWNERSHIP[agent]):
            continue
        if file_path.startswith("ui/") and file_path not in {"ui/dashboard/__init__.py", "ui/dashboard/view.py"} and agent in {"agent8", "agent9"}:
            if agent == "agent8":
                continue
        violations.append(file_path)

    if violations:
        print("Violations:")
        for item in sorted(set(violations)):
            print(item)
        return 1
    print(f"{agent}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
