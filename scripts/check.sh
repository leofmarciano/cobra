#!/usr/bin/env bash
# Local lint/test script matching the CI workflow.
# Usage: ./scripts/check.sh [--ci]
# --ci    exits non-zero on the first job failure (default: runs all jobs)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export ROOT

cd "$ROOT"

CI_MODE="${1:-}"
if [ "$CI_MODE" = "--ci" ]; then
  set -e
fi

FAILURES=0

run() {
  echo "==> $1"
  if ! "${@:2}"; then
    echo "FAILED: $1" >&2
    FAILURES=$((FAILURES + 1))
    [ "$CI_MODE" = "--ci" ] && return 1
  fi
}

# Python environment
run "uv sync" uv sync --locked

# Python lint/format/type/test
run "python-lint" bash "$ROOT/scripts/ci/python-lint.sh"
run "python-test" bash "$ROOT/scripts/ci/python-test.sh"

# Repository health: deps and dead code (Python)
run "python-health" bash "$ROOT/scripts/ci/python-health.sh"

# Config lint: JSON (biome), YAML, Markdown, Shell, EditorConfig
run "config-lint" bash "$ROOT/scripts/ci/config-lint.sh"

# Knip: unused config files / npm deps
if [ -f package.json ]; then
  run "knip" bash "$ROOT/scripts/ci/knip.sh"
fi

# Build smoke: CMake configure only (no C++ sources yet)
if [ -f CMakeLists.txt ]; then
  run "build-smoke" bash "$ROOT/scripts/ci/build-smoke.sh"
fi

# Orchestration smoke: the loop harness parses state cleanly
run "orchestration-smoke" bash "$ROOT/scripts/ci/orchestration-smoke.sh"

if [ "$FAILURES" -gt 0 ]; then
  echo "ERROR: $FAILURES check(s) failed" >&2
  exit 1
fi

echo "All checks passed."
