#!/usr/bin/env bash
# Lint non-Python repository files: JSON (biome), YAML, Markdown, shell, editorconfig.
set -euo pipefail

cd "$(dirname "$0")/../.."

if [ -f package.json ] && command -v npx >/dev/null 2>&1; then
  # Biome: JSON/JSONC/JS/TS/CSS
  npx biome check . --error-on-warnings

  # Markdown — config in .markdownlint-cli2.jsonc
  npx markdownlint-cli2 "**/*.md" "#node_modules" "#.venv"
fi

# YAML
uv run yamllint -c .yamllint .github/workflows .yamllint .pre-commit-config.yaml .github/dependabot.yml

# Shell scripts (skip if not installed locally)
if command -v shellcheck >/dev/null 2>&1; then
  find . -path ./node_modules -prune -o -path ./.venv -prune -o -name '*.sh' -type f -print0 |
    xargs -0 -r shellcheck
fi

# EditorConfig (skip if not installed locally)
if command -v editorconfig-checker >/dev/null 2>&1; then
  editorconfig-checker
fi
