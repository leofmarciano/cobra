#!/bin/bash
# Wrapper for the Cobra autonomous Orca-backed sprint-loop harness.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

exec python3 "$REPO_ROOT/scripts/cobra_orca_loop.py" "$@"
