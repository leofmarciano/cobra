#!/usr/bin/env bash
# Python lint, format and type checks.
set -euo pipefail

cd "$(dirname "$0")/../.."

uv run ruff check .
uv run ruff format --check .
uv run mypy python/cobra_compiler
uv run mypy benchmarks/harness/src/cobra_bench --strict
uv run --directory benchmarks/pipelines mypy src/cobra_pipelines --strict
