# S06 — Toolchain pinning & dev container

| Field | Value |
|---|---|
| GitHub issue | #7 |
| Milestone | M1 — Compiler skeleton |
| Depends on | S05 = go |
| Hardware | CPU-only (container must also build on the GPU host) |
| Estimated sessions | 2-3 |
| Plan sections | §15.2, §16.2, §34.1, §29 (Days 31-45 start) |

## Objective

Pin the native toolchain (LLVM/MLIR, CMake presets, compilers, caching)
and produce a reproducible dev container so every future native sprint
builds identically. This sprint ends when a trivial MLIR-linked tool
builds from a clean clone in the container and in CI.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §15.2 (toolchain list), §16.2 (build
   outputs), §34.1 (local sequence)
3. `support-matrix.yaml` (S02 pins)

## Out of scope

- Cobra dialects (S07). CUDA kernels. Release/LTO builds. Windows/macOS
  native support (container only on macOS).

## Tasks

### T1 — LLVM/MLIR pin + acquisition script (ADR-0006)
- [ ] Do: choose the latest stable LLVM release line, verify MLIR is
  buildable/usable from it; write `scripts/get-llvm.sh` that either
  downloads a prebuilt MLIR distribution or builds from source with
  ccache into `third_party/llvm/` (out of git). Record exact
  version/commit + rationale in `docs/decisions/ADR-0006-llvm-pin.md`
  and `support-matrix.yaml`.
- Accept: script is idempotent; re-run is a no-op; version is pinned by
  hash, not "latest".

### T2 — CMake superstructure + presets
- [ ] Do: root `CMakeLists.txt` (C++20, hidden visibility default,
  warnings-as-errors for our code) + `CMakePresets.json` with presets:
  `dev`, `release`, `asan-ubsan`, `tsan`, `fuzz` (stubs allowed for
  fuzz until S10). Wire `find_package(MLIR)` against the T1 install.
  Add a smoke tool `tools/cobra-smoke/` that parses a trivial builtin
  MLIR module and prints it (proves headers+libs link).
- Accept: `cmake --preset dev && cmake --build --preset dev` produces
  `cobra-smoke`; it round-trips a builtin-dialect snippet.

### T3 — Dev container
- [ ] Do: `docker/dev.Dockerfile` — CUDA-enabled base (matching
  support-matrix CUDA line), clang+lld, cmake+ninja+ccache, uv, Python
  pin; non-root user; `docker/README.md` with build/run one-liners
  (mount repo, ccache volume). Verify the container ALSO runs on the
  GPU host with `--gpus all`.
- Accept: clean `docker build` + in-container preset build of T2 works;
  documented commands copy-paste correctly.

### T4 — Native CI lane
- [ ] Do: `.github/workflows/native-build.yml`: build the container (or
  pull a cached image), run dev-preset build + `cobra-smoke` check +
  ctest placeholder. Cache ccache between runs.
- Accept: workflow YAML valid; lane passes on a clean runner
  (if GitHub runners lack resources for full LLVM, the prebuilt-download
  path from T1 must make this feasible — that is a T1 design
  constraint).

### T5 — Build documentation
- [ ] Do: `docs/guides/building.md`: prerequisites, container flow,
  bare-Linux flow, GPU-host flow, ccache notes, troubleshooting; update
  `scripts/check.sh` to include the native build when in a native
  environment (skip cleanly otherwise).
- Accept: a fresh executor can build following ONLY this doc (validator
  will literally do this).

## Validation

```bash
./scripts/get-llvm.sh
cmake --preset dev && cmake --build --preset dev
./build/dev/bin/cobra-smoke --version
docker build -f docker/dev.Dockerfile -t cobra-dev .
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; container + bare build green; CI lane green
- [ ] ADR-0006 committed; support-matrix updated
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S07 (dialects) and S08 (runtime core) both build on these presets. S07
needs TableGen working (`mlir-tblgen` available from the T1 install).

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
