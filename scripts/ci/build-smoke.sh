#!/usr/bin/env bash
# Smoke-test that the CMake configure step is well-formed.
set -euo pipefail

cd "$(dirname "$0")/../.."

BUILD_DIR="build/ci-smoke"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cmake -S . -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE=Release -DCOBRA_BUILD_TESTS=OFF
