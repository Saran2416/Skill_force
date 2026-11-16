#!/usr/bin/env bash
set -euo pipefail

branches=(
  "agent1-data"
  "agent2-skills"
  "agent3-company"
  "agent4-matcher"
  "agent5-planner"
  "agent6-assessor"
  "agent7-mentor"
  "agent8-ui"
  "agent9-dashboard"
)

for branch in "${branches[@]}"; do
  target="../skillforce-${branch}"
  if [ ! -d "$target" ]; then
    git worktree add "$target" "$branch"
  fi
done
