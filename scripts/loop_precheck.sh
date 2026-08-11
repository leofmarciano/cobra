#!/bin/bash
# Precheck used by the Orca automation to avoid overlapping loop runs.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIDFILE="$REPO_ROOT/scripts/.cobra_loop.pid"

if [[ -f "$PIDFILE" ]]; then
  PID="$(cat "$PIDFILE")"
  if kill -0 "$PID" 2>/dev/null; then
    echo "Cobra loop already running (PID $PID); skipping scheduled run." >&2
    exit 1
  fi
  # Stale pidfile: remove it so the next run can start.
  rm -f "$PIDFILE"
fi

exit 0
