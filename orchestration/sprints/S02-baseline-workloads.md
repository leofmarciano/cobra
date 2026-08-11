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
- [ ] Do: run `cobra-bench doctor --strict` on the Linux GPU host; commit
  `artifacts/environment/primary-host.json`; fill STATE.md Environment
  table (OS/kernel/CPU/RAM/GPU/driver/CUDA). Pin framework versions
  chosen here into `support-matrix.yaml` (torch, pandas, cudf, numpy,
  pyarrow — latest stable, ≥7 days old).
- Accept: STATE.md updated; doctor strict passes on host.

### T1 — Workload 1: `parquet_feature_inference`
- [ ] Do: seeded synthetic Parquet generator (~1-5M rows, mixed dtypes
  incl. nulls + categoricals); pipeline: read_parquet → filter →
  feature engineering (pandas) → tensor conversion → small MLP inference
  (torch) → projection. Correctness oracle: exact for
  integers/strings/index, per-dtype tolerances for floats (document
  values in the workload README per §33.4).
- Accept: `cobra-bench verify` passes; dataset generation deterministic
  (hash-stable across runs).

### T2 — Workload 2: `model_ensemble`
- [ ] Do: one input batch → two independent torch models (different
  architectures, e.g., MLP + small transformer encoder — record choices)
  → weighted aggregation. This is the parallel-branch opportunity
  workload (§2.4).
- Accept: oracle passes; both branches provably independent (no shared
  mutable state) — assert in test.

### T3 — Workload 3: `cv_preprocess_inference_postprocess`
- [ ] Do: synthetic image batch → CPU preprocessing (resize/normalize,
  numpy or torchvision transforms) → torchvision model (e.g., resnet18,
  pinned weights) → postprocessing (top-k + thresholding). The mixed
  CPU/GPU transition workload.
- Accept: oracle passes; preprocessing measurably CPU-bound (documented).

### T4 — B0 and B1 variants
- [ ] Do: for each workload, `b0` = plain eager; `b1` = strongest
  automatic composition: `torch.compile` on models + `cudf.pandas`
  acceleration where applicable (§20.2 — B1 must NOT include manual
  restructuring). Document exact flags/modes per variant in the workload
  README. Wire as suite `benchmarks/suites/phase0.yaml`.
- Accept: all six variant×workload combos run green through the harness.

### T5 — Baseline measurement + profiler evidence
- [ ] Do: on the GPU host: `verify` then `run` (cold + warm, ≥30 samples)
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
