#!/usr/bin/env bash
set -euo pipefail
# Run from the repository root with GitHub CLI installed and authenticated.
repo_name="${1:-adk-agent-suite}"
visibility="${2:---private}"
case "$visibility" in --private|--public) ;; *) echo 'Visibility must be --private or --public' >&2; exit 2 ;; esac
command -v gh >/dev/null || { echo 'Install GitHub CLI, then run gh auth login.' >&2; exit 1; }
gh auth status
git rev-parse --git-dir >/dev/null 2>&1 || git init -b main
git add .
if ! git diff --cached --quiet; then git commit -m "Build five end-to-end ADK agents and walkthrough artifacts"; fi
if git remote get-url origin >/dev/null 2>&1; then
  git push -u origin HEAD
else
  gh repo create "$repo_name" "$visibility" --source . --remote origin --push
fi
gh repo view --json url --jq .url
