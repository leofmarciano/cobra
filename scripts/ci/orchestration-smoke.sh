#!/usr/bin/env bash
# Smoke-test the autonomous loop harness: dry-run and parse existing state.
set -euo pipefail

cd "$(dirname "$0")/../.."

./scripts/cobra_orca_loop.sh --dry-run --once
