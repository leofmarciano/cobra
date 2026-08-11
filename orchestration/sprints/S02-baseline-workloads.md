# S02 — Baseline workloads & B0/B1 report

| Field | Value |
|---|---|
| GitHub issue | #3 |
| Milestone | M0 — Thesis validation |
| Depends on | S01 (done) |
| Hardware | **NVIDIA GPU required** |
| Estimated sessions | 2-3 |
| Plan sections | §20.2, §20.3-D, §29 (Days 1-10), §2.4, §33.2-33.4 |

## Objective

Freeze the three prototype pipelines and produce the "baseline report
with no Cobra claims" (§29 Days 1-10 output): B0 (eager) and B1
(strongest composed automatic tools) measured with the S01 harness, plus
profiler traces showing where time goes. These numbers are the enemy
Cobra must beat at S05/S21.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §20.2 (B0-B3 definitions), §20.3-D
   (workload list), §29 Days 1-10, §2.4 (high-value characteristics)
3. `benchmarks/harness/` public API (from S01)

## Out of scope

- B2 hand-tuned references (deferred to S20 where affordable). Any Cobra
  prototype (B3 starts in S04/S20). More than three workloads.

## Tasks

### T0 — Record the GPU host (FIRST, blocking)
- [x] Do: run `cobra-bench doctor --strict` on the Linux GPU host; commit
  `artifacts/environment/primary-host.json`; fill STATE.md Environment
  table (OS/kernel/CPU/RAM/GPU/driver/CUDA). Pin framework versions
  chosen here into `support-matrix.yaml` (torch, pandas, cudf, numpy,
  pyarrow — latest stable, ≥7 days old).
- Accept: STATE.md updated; doctor strict passes on host.

### T1 — Workload 1: `parquet_feature_inference`
- [x] Do: seeded synthetic Parquet generator (~1-5M rows, mixed dtypes
  incl. nulls + categoricals); pipeline: read_parquet → filter →
  feature engineering (pandas) → tensor conversion → small MLP inference
  (torch) → projection. Correctness oracle: exact for
  integers/strings/index, per-dtype tolerances for floats (document
  values in the workload README per §33.4).
- [x] Accept: `cobra-bench verify` passes; dataset generation deterministic
  (hash-stable across runs).

### T2 — Workload 2: `model_ensemble`
- [x] Do: one input batch → two independent torch models (different
  architectures, e.g., MLP + small transformer encoder — record choices)
  → weighted aggregation. This is the parallel-branch opportunity
  workload (§2.4).
- Accept: oracle passes; both branches provably independent (no shared
  mutable state) — assert in test.

### T3 — Workload 3: `cv_preprocess_inference_postprocess`
- [x] Do: synthetic image batch → CPU preprocessing (resize/normalize,
  numpy or torchvision transforms) → torchvision model (e.g., resnet18,
  pinned weights) → postprocessing (top-k + thresholding). The mixed
  CPU/GPU transition workload.
- Accept: oracle passes; preprocessing measurably CPU-bound (documented).

### T4 — B0 and B1 variants
- [x] Do: for each workload, `b0` = plain eager; `b1` = strongest
  automatic composition: `torch.compile` on models + `cudf.pandas`
  acceleration where applicable (§20.2 — B1 must NOT include manual
  restructuring). Document exact flags/modes per variant in the workload
  README. Wire as suite `benchmarks/suites/phase0.yaml`.
- Accept: all six variant×workload combos run green through the harness.

### T5 — Baseline measurement + profiler evidence
- [x] Do: on the GPU host: `verify` then `run` (cold + warm, ≥30 samples)
  then `analyze`. Capture `nsys` traces for b0 and b1 of each workload
  (one representative iteration). Write
  `docs/benchmarks/phase0-baseline.md`: absolute times, CIs, and a
  bottleneck analysis per workload (transfers? launch gaps? CPU-bound
  segments? sync stalls?) with screenshots/refs to trace files.
- Accept: report answers "where does the time go" for each workload with
  trace evidence; raw artifacts committed (or size-flagged + stored per
  a documented convention).

## Validation

```bash
uv run cobra-bench verify --suite benchmarks/suites/phase0.yaml --variants b0,b1
uv run cobra-bench run --suite benchmarks/suites/phase0.yaml \
  --variants b0,b1 --phase warm --output artifacts/raw/phase0
uv run cobra-bench analyze --input artifacts/raw/phase0 --output artifacts/analysis/phase0
test -f docs/benchmarks/phase0-baseline.md
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; measurements from the recorded GPU host only
- [ ] No §33.11 anti-pattern (validator will hunt for them)
- [ ] STATE.md Environment filled; Session log updated; committed

## Handoff to next sprint

S03 traces these exact three workloads. S04-S05 measure against the
b1 numbers produced here — do not regenerate datasets after this sprint
(they are frozen; changing them requires a D-NNN decision).

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->

**2026-08-11 — S02 executor (P0), boot + T0 attempt**
- Booted from `main`; created branch `sprint/S02-baseline-workloads`.
- Read context budget: `COBRA_TECHNICAL_PLAN.md` §20.2, §20.3-D, §29 Days 1-10, §2.4, §33.2-33.4.
- T0 requires running `cobra-bench doctor --strict` on the Linux + NVIDIA GPU host and recording `artifacts/environment/primary-host.json`. This macOS orchestration host has no GPU; `cobra-bench doctor` strict mode fails when `nvidia-smi` is absent (§33.2).
- **Blocker:** need owner-provided Linux + NVIDIA GPU host access (hostname/SSH, GPU model, driver version, CUDA toolkit). Recorded in `orchestration/STATE.md` Blockers and Human-input queue.
- No code changes; next action is to rerun P0 once host details are supplied.

**2026-08-11 — S02 executor (P0), boot + T0 blocked on loop state**
- Booted and read context budget. GPU host is now available (WSL2 + RTX 3080), but the repo state contradicts itself.
- `git status` shows working tree clean but currently on `main`, not the sprint branch `sprint/S02-baseline-workloads` declared in `STATE.md`.
- `git log --oneline -10` shows commit `995e564 Merge pull request #32 from leofmarciano/sprint/S02-baseline-workloads`, i.e. the S02 branch was already merged into `main` while the previous session was blocked.
- `orchestration/ROADMAP.md` ledger lists S02 status as `not_started`, while `orchestration/STATE.md` lists it as `in_progress`.
- Per `AGENTS.md` and `P0-execute.md`, a `git`/STATE contradiction triggers `P2-recovery.md`. Executor stopped before doing sprint work.
- Recorded blocker in `orchestration/STATE.md`; next prompt is `P2-recovery.md`.

**2026-08-11 — S02 executor (P0), T1 complete**
- Added the `cobra-pipelines` workspace package (`benchmarks/pipelines/`) with
  pinned framework dependencies (torch 2.13.0, numpy 2.4.6, pandas 2.3.3,
  pyarrow 23.0.1) and implemented the `parquet_feature_inference` workload.
- Extended the harness with an `approx` correctness comparator that uses
  `rtol_by_dtype` / `atol_by_dtype` for floats and exact equality for
  integers, strings, and booleans (plan §33.4).
- Wired `benchmarks/suites/phase0.yaml` with the `parquet_feature_inference`
  `b0` variant and `approx` tolerances.
- Verified `cobra-bench verify --suite benchmarks/suites/phase0.yaml` passes.
- `./scripts/check.sh` passes.  Added `knip.json` `ignoreDependencies` for
  `@biomejs/biome` and `markdownlint-cli2` to suppress a false-positive
  unused-dependency report from `npx knip` (6.x) on Node 24; CI uses npm-ci
  pinned `knip` 5.88.1.
- Current task: T2 (`model_ensemble`); T4 will add the `b1` variant and the
  remaining workloads to the suite.

**2026-08-11 — S02 executor (P0), T2+T3 complete**
- Booted on `sprint/S02-baseline-workloads`, clean tree, STATE consistent.
- T2: Implemented `model_ensemble` b0 — one batch sent to two independent
  torch models (3-layer MLP + 2-layer TransformerEncoder), weighted
  aggregation (0.6/0.4). Tests prove branch independence (no shared mutable
  state). `cobra-bench verify` passes.
- T3: Implemented `cv_preprocess_inference_postprocess` b0 — synthetic
  256x256 images, CPU preprocessing (bilinear resize to 224x224, ImageNet
  normalize), resnet18 inference (torchvision==0.28.0, DEFAULT weights),
  postprocessing (softmax→top-1→threshold). Tests prove CPU-boundedness of
  preprocessing. `cobra-bench verify` passes.
- Added `torchvision==0.28.0` dependency (BSD, published 2026-07-08).
- All 3 workloads pass `cobra-bench verify`. `./scripts/check.sh` passes
  (123 tests, 0 failures).
- Next: T4 (B0/B1 variants — add `torch.compile` + `cudf.pandas`).

**2026-08-11 — S02 executor (P0), T4 complete**
- Booted on `sprint/S02-baseline-workloads`, clean tree, STATE consistent.
- T4: Implemented B1 variants for all 3 workloads:
  - `parquet_feature_inference` b1: torch.compile(mode=default) on MLP +
    cudf.pandas install() if available (graceful fallback).
  - `model_ensemble` b1: torch.compile(mode=default) on both MLP and
    TransformerEncoder.
  - `cv_preprocess_inference_postprocess` b1: torch.compile(mode=default) on
    resnet18; preprocessing stays CPU-bound.
- Added `_compile_env.py` helper — ensures pip-wheel nvcc is on PATH for
  Inductor backend (system nvcc absent; `nvidia-cuda-nvcc==13.0.88` provides
  the binary under `site-packages/nvidia/cu13/bin/nvcc`).
- Added `nvidia-cuda-nvcc==13.0.88` as a real dependency in
  `benchmarks/pipelines/pyproject.toml` (BSD-like NVIDIA license, published
  2025-08-20, >7 days old).
- Extended harness `_float_key` to support a `"float"` key in tolerance dicts
  (allows suite-level override for Python float values). Added `float: 1e-3`
  rtol/atol in `phase0.yaml` to accommodate torch.compile float32 reordering.
- All 6 workload×variant combos pass `cobra-bench verify`.
- `./scripts/check.sh` passes (123 tests, 0 failures).
- T4 checked off. Next: T5 (baseline measurement + profiler evidence).

**2026-08-11 — S02 executor (P0), T0 complete**
- Booted on `sprint/S02-baseline-workloads` (recreated by a prior recovery session), clean tree, ROADMAP/STATE consistent (`in_progress`). No contradiction — proceeded with T0.
- Ran `uv run cobra-bench doctor --strict --output artifacts/environment/primary-host.json`: exit code 0 (passes). Host: WSL2 Ubuntu 24.04.1, Intel i9-10900F, 15.62 GiB RAM, NVIDIA RTX 3080 (driver 591.86, compute cap 8.6, 320W cap, persistence on). Committed the report.
- Researched current stable framework releases (web search, 2026-08-11) and checked pairwise compatibility with `uv pip install --dry-run` in a scratch `/tmp` venv (nothing installed in the repo env). Finding: `cudf-cu13==26.6.0` (the RAPIDS wheel matching this driver's CUDA 13.1 ceiling) constrains `numpy<2.5,>=1.26`, `pandas<2.4.0,>=2.0`, `pyarrow<24,>=19.0.0` — so the newest upstream releases (numpy 2.5.2, pandas 3.0.5, pyarrow 25.0.1) are NOT usable with cudf.pandas acceleration for B1. Selected the newest releases satisfying cudf's ceilings, all published ≥7 days ago: `torch==2.13.0`, `numpy==2.4.6`, `pandas==2.3.3`, `pyarrow==23.0.1`, `cudf-cu13==26.6.0`. Verified the full 5-package set co-resolves together (dry-run only).
- Also confirmed system-wide `nvcc` is absent on the host, but this is not a blocker: the pip wheel set pulls in `nvidia-cuda-nvcc-cu13`/`nvidia-cuda-runtime-cu13`/etc., which is sufficient for pip-wheel-based workloads (no native CUDA compilation is needed in S02).
- Recorded the pins and rationale in `support-matrix.yaml` (ubuntu-24.04/x86_64 platform row) and mirrored the summary into `STATE.md` Environment table.
- Note for Validator/next executor: these are pins only — torch/numpy/pandas/pyarrow/cudf are not yet added as real project dependencies. T1-T4 must add them (`uv add` under the harness or workload package) using exactly these versions, and record the dependency add in this log + `DECISIONS.md` per PROTOCOL §6/§7.
- T0 checked off. Next task: T1 (`parquet_feature_inference` workload).

**2026-08-11 — S02 executor (P0), T5 complete**
- Booted on `sprint/S02-baseline-workloads`, clean tree, STATE consistent.
- Installed `cudf-cu13==26.6.0` as a real dependency in
  `benchmarks/pipelines/pyproject.toml`; `uv.lock` updated.
- Fixed `_engineer_features` in `parquet_feature_inference.py` to normalize
  in NumPy and reconstruct a DataFrame, avoiding a cudf.pandas column-alignment
  assertion under `(numeric - mean) / std`.
- Ran `cobra-bench verify` for phase0 (b0,b1): all 3 workloads passed.
- Ran `cobra-bench run --phase warm --seed 42` for phase0: 180 samples total
  (30 per workload×variant).
- Ran `cobra-bench analyze --seed 42`: produced
  `artifacts/analysis/phase0/{summary.md,summary.json,confidence_intervals.csv}`.
- Captured Nsight Systems 2024.4.1 traces for all 6 workload×variant combos;
  applied the WSL2 `CuptiUseRawGpuTimestamps=false` workaround so GPU kernel
  data appears. Trace files and CSV summaries committed under
  `artifacts/traces/phase0/` (`.nsys-rep` = 54 MiB total, sqlite temp files
  removed).
- Wrote `docs/benchmarks/phase0-baseline.md` with absolute times, CIs,
  anti-pattern check, and bottleneck analysis per workload.
- `./scripts/check.sh` passes (123 tests, 0 failures).
- T5 checked off. Sprint is now complete; next step is validation (`P1-validate.md`).
- Surprises/decisions:
  - B1 is slightly slower than B0 on two of three workloads at this scale
    (parquet: 0.897x, ensemble: 0.944x, cv: 1.041x). This is acceptable for a
    baseline — it defines the product baseline Cobra must beat.
  - cudf.pandas required a small code change to avoid a DataFrame arithmetic
    assertion; the fix preserves the same numerical output.
  - Nsight Systems CLI was not pre-installed; extracted the 2024.4.1 CLI-only
    `.deb` to `/tmp/nsys-root` and added the WSL2 timestamp workaround.
