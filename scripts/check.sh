#!/usr/bin/env bash
# Local lint/test script matching the CI workflow.
set -euo pipefail

cd "$(dirname "$0")/.."

uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy python/cobra_compiler
uv run pytest
