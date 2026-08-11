# S15 — Scheduler overhead benchmarks & granularity control

| Field | Value |
|---|---|
| Milestone | M2 — Runtime & scheduler (closes it) |
| Depends on | S14 (done) |
| Hardware | **NVIDIA GPU required** |
| Estimated sessions | 1-2 |
| Plan sections | §8.6, §20.3-A, §13.1 (calibration inputs), §28 (overhead risk row) |

## Objective

Prove the runtime is cheap enough to be worth using ("Scheduler overhead
exceeds saved time" is a plan-listed critical risk). Build the native
microbenchmark suite, calibrate per-machine task overhead, and implement
granularity control v0 (min-cost threshold + coarsening) driven by
measured numbers — "thresholds must be calibrated, not permanently
hard-coded" (§8.6).

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §8.6 (mechanism list), §20.3-A (micro
   suite), §13.1 (cost inputs)
3. `runtime/` public headers (S08/S13/S14)

## Out of scope

- The cost MODEL (S19). Fusion of tensor KERNELS (backend job). Python-
  side dispatch overhead beyond one bridge benchmark (S12 measured
  fallback overhead).

## Tasks

### T1 — Google Benchmark suite (native)
- [ ] Do: `benchmarks/micro/native/`: scheduler enqueue+dispatch,
  dependency resolution per edge, promise/event signal, CUDA event
  create vs reuse, stream acquire/release, pool alloc/free (host,
  pinned, device), h2d/d2h small-copy latency, empty-kernel launch,
  cancellation propagation (§20.3-A list, single-GPU rows). Google
  Benchmark added via CMake (pinned version ≥7 days old).
- Accept: suite runs via one target; JSON output lands in
  `artifacts/analysis/micro/`; each bench has stable units.

### T2 — Machine calibration tool
- [ ] Do: `tools/cobra-calibrate/` (or script): runs T1 + derives the
  §13.1 calibration constants (per-task scheduling overhead ns, per-
  event overhead, copy latency curve small/medium/large, launch
  overhead) → writes versioned `calibration.json` keyed by machine
  fingerprint (host+GPU+driver). Store the GPU host's file under
  `artifacts/environment/`.
- Accept: two consecutive runs agree within documented CoV; file schema
  documented in `docs/reference/calibration-format.md`.

### T3 — Granularity control v0
- [ ] Do: implement in the S13 planner: minimum-task-cost threshold
  (from calibration, not constants), adjacent small-task fusion (chain
  collapse where effects permit), max ready-queue depth, bounded
  stream count already enforced (S14) (§8.6 mechanisms 1-4, 6-7).
- Accept: sim tests — a 1000-tiny-node chain collapses to few tasks;
  a mixed DAG keeps large nodes unfused; threshold provably read from
  calibration file (test with synthetic calibration).

### T4 — Overhead budget + risk memo
- [ ] Do: `docs/benchmarks/runtime-overhead.md`: measured per-task
  overhead vs the S04 experiment gains — compute the minimum task size
  (µs) for which Cobra scheduling is profitable on the reference host;
  state the v0.1 budget (used by S19's profitability gate and S28's
  qualification).
- Accept: memo cites benchmark JSON; budget number explicit.

## Validation

```bash
cmake --build --preset release --target cobra-micro-bench
./build/release/bin/cobra-micro-bench --benchmark_format=json \
  > artifacts/analysis/micro/latest.json
./build/release/bin/cobra-calibrate --output /tmp/calibration.json
ctest --preset dev -R granularity
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; calibration committed for the GPU host
- [ ] Overhead budget memo exists with explicit numbers
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

M2 done. S16 begins framework integration. S19 consumes
`calibration.json` as cost-model input; S28 re-runs T1 to verify the
"scheduler overhead meets the v0.1 microbenchmark budget" gate (Epic 8).

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
