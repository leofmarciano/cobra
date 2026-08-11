#!/usr/bin/env bash
# Dependency and dead-code health for the Python package.
set -euo pipefail

cd "$(dirname "$0")/../.."

# deptry: find missing or unused pyproject dependencies
uv run deptry python/cobra_compiler

# vulture: find unused Python code (temporary whitelist until the project grows)
uv run vulture python/cobra_compiler test/python \
  --exclude 'python/cobra_compiler/__init__.py' \
  --min-confidence 80
