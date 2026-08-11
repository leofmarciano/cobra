#!/usr/bin/env bash
# Python test suite.
set -euo pipefail

cd "$(dirname "$0")/../.."

uv run pytest test/python benchmarks/harness benchmarks/pipelines experimental/tracer -q -m "not gpu"
