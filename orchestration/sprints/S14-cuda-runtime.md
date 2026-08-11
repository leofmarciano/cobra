# S14 — CUDA runtime (streams, events, memory)

| Field | Value |
|---|---|
| Milestone | M2 — Runtime & scheduler |
| Depends on | S13 (done) |
| Hardware | **NVIDIA GPU required** |
| Estimated sessions | 3-4 |
| Plan sections | §12.3, §12.6, §11.4-11.5, §19.13-19.14, §29 (Days 61-75) |

## Objective

Give the scheduler real hardware: CUDA device manager, bounded stream
and event pools, copy streams, device memory pool with reservations,
failure propagation, and cancellation-as-draining. Exit = the §29 Days
61-75 output: *"safe one-GPU parallel fan-out and fan-in through the
actual runtime."*

## Context budget (read ONLY these)

1. `orchestration/STATE.md` (GPU host details), this file
2. `COBRA_TECHNICAL_PLAN.md` §12.3 (device ownership), §12.6
   (cancellation/draining), §11.4 (memory planning features), §11.5
   (OOM policy), §19.14 (failure injection list)
3. `runtime/core/scheduler/` contracts (S13), S08 allocator interface

## Out of scope

- CUDA Graphs (S19). Multi-GPU/NCCL (beta). Kernel GENERATION (Triton —
  S19+ via backends). NUMA/pinned-pool tuning beyond a working pinned
  pool. cuDF/torch integration (S16-S18).

## Tasks

### T1 — Device + stream + event management
- [ ] Do: `runtime/cuda/`: device enumeration/capabilities registry;
  per-device: one default compute stream, bounded extra compute-stream
  pool, ≥1 dedicated copy stream, event pool with reuse (§12.3). RAII
  everywhere; every CUDA call checked; errors map to S08 `Status` with
  device context. CMake gains a `CUDA` component gated by
  `COBRA_ENABLE_CUDA` (CPU-only builds stay green).
- Accept: unit tests on GPU host: pool bounds respected, event reuse
  works, error mapping tested via invalid-arg calls.

### T2 — Schedule execution on real CUDA
- [ ] Do: implement the S13 fake-device API against real devices:
  task launch onto assigned streams, cross-stream deps via events (no
  global sync — §12.3), h2d/d2h on copy streams with event ordering,
  host-callback completion into the executor.
- Accept: integration test — fan-out of two GPU tasks (cheap kernels
  via driver API or CUDA runtime saxpy-style test kernels) + fan-in
  runs correctly 1000x; nsys trace artifact shows overlap (committed
  as evidence, path in Session log).

### T3 — Device memory pool + reservations
- [ ] Do: device pool implementing S08 `Allocator` (stream-ordered
  allocation OR pool-with-events — document the choice), reservation
  API for planned peak (§11.4), stream-aware release, stats (peak,
  in-use, reuse). OOM path implements §11.5 steps 1/2/5/6 (reduce
  concurrency hook, cache release hook, retry-smaller once, eager
  fallback signal) — steps 3/4 (backend workspace, spill) are stubs
  with TODO-issue refs.
- Accept: allocation-storm test stays within cap; forced-OOM test
  walks the policy ladder and NEVER silently loops (§11.5).

### T4 — Failure injection + cancellation drain
- [ ] Do: deterministic failure points (§19.14 subset): CUDA alloc
  failure, launch failure, sync failure, canceled request → verify:
  resources released (streams/events returned, memory freed), useful
  error surfaced with schedule context, no partially-valid output
  handed to Python; cancellation drains submitted GPU work (§12.6:
  cannot forcibly remove) while suppressing unused outputs.
- Accept: each injection point has a test; leak counters return to
  baseline after every failure test.

### T5 — compute-sanitizer lane
- [ ] Do: script + CI (GPU runner if available; else documented manual
  lane run on the GPU host per PROTOCOL): `compute-sanitizer --tool
  memcheck` and `--tool racecheck` over the CUDA test binary (§34.4
  shape); record results in Session log.
- Accept: memcheck + racecheck clean on the full S14 test suite.

## Validation

```bash
cmake --preset dev -DCOBRA_ENABLE_CUDA=ON && cmake --build --preset dev
ctest --preset dev -R cuda
compute-sanitizer --tool memcheck ./build/dev/bin/cobra-cuda-tests
compute-sanitizer --tool racecheck ./build/dev/bin/cobra-cuda-tests --gtest_filter='Scheduler*'
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; overlap evidence (nsys) committed
- [ ] CPU-only build still green (CUDA properly optional)
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S15 measures this runtime's overhead and calibrates granularity
thresholds. S16/S18 run tensors through these streams/pools. The
stream/event contract is now frozen for v0.1 — changes need a D-NNN.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
