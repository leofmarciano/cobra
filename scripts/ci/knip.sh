#!/usr/bin/env bash
# Knip: find unused npm devDependencies and dead config files.
set -euo pipefail

cd "$(dirname "$0")/../.."

npx knip --no-progress
