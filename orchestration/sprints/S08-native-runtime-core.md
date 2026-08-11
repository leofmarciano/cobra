# S08 — Native runtime core (CPU)

| Field | Value |
|---|---|
| GitHub issue | #9 |
| Milestone | M1 — Compiler skeleton |
| Depends on | S06 (done) — independent of S07, but runs after (WIP=1) |
| Hardware | CPU-only |
| Estimated sessions | 2-3 |
| Plan sections | §12.1-12.2, §12.6, §8.3, §35 Epic 8 (CPU subset) |

## Objective

Build the CPU half of the runtime: task graph executor, thread pool,
promises/events, error+cancellation model, and allocator interfaces —
with GoogleTest coverage and sanitizer-clean builds. CUDA arrives in S14
on top of these abstractions.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §12.1 (component list), §12.2 (CPU rules),
   §12.6 (cancellation states), §8.3 (exception policy)
3. `docs/decisions/ADR-0005-semantic-charter.md` (exception/commit rules)

## Out of scope

- CUDA anything (S14). Work-stealing optimization (simple queue first;
  §8.6 calibration comes in S15). NUMA awareness (beta). Python bindings
  (S09). Scheduling POLICY (S13 — this sprint is mechanism only).

## Tasks

### T1 — Core value & error types
- [ ] Do: `runtime/core/`: `Status`/`StatusOr` (or `expected`-based)
  error model with error codes + source info; `CancellationToken`
  implementing the §12.6 state machine (not_started/submitted/running/
  completed/failed/cancel_requested/abandoned_draining); GoogleTest up
  via CMake (`check-cobra-unit` target).
- Accept: state-machine unit tests cover every legal transition and
  reject illegal ones.

### T2 — Task and TaskGraph
- [ ] Do: `Task` = callable + declared deps + source-order index (§8.3);
  `TaskGraph` = DAG container with cycle detection, topological
  iteration, and readiness tracking. No execution yet.
- Accept: unit tests: cycle rejection, topo order stability,
  readiness updates on completion.

### T3 — Executor (thread pool) + promises
- [ ] Do: fixed-size thread pool (configurable), `Promise`/`Future`
  pair or event objects for completion; executor runs a TaskGraph
  respecting deps; failure propagation per §8.3: earliest
  source-order failure wins, later failures attached as suppressed
  diagnostics; cooperative cancellation of not-yet-started tasks.
- Accept: tests: fan-out/fan-in, two concurrent failures → deterministic
  winner (run 1000x), cancellation prevents queued tasks, no
  use-after-free under ASan when graph outlives executor misuse.

### T4 — Allocator interface + host pool v0
- [ ] Do: `Allocator` interface (allocate/deallocate/stats + alignment);
  `HostPoolAllocator` v0 (free-list by size class, stats counters:
  bytes in use, peak, reuse count). Buffer handle carries owner +
  storage identity groundwork for §11.3.
- Accept: pool reuse test (alloc/free/alloc same class reuses),
  stats accuracy test, leak-free under LSan.

### T5 — Sanitizer qualification
- [ ] Do: ensure `asan-ubsan` and `tsan` presets build and run
  `check-cobra-unit`; fix all findings; add a stress test (random DAGs,
  random failures/cancels, 10k tasks) run under TSan.
- Accept: both presets green; stress test deterministic via seed.

## Validation

```bash
cmake --build --preset dev --target check-cobra-unit
cmake --preset asan-ubsan && cmake --build --preset asan-ubsan --target check-cobra-unit && ctest --preset asan-ubsan
cmake --preset tsan && cmake --build --preset tsan --target check-cobra-unit && ctest --preset tsan
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; ASan/UBSan/TSan green (plan Phase 1 exit)
- [ ] Public headers under `include/cobra/runtime/` documented
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S09 executes captured two-node DAGs through this executor. S13 builds
the scheduling POLICY layer on TaskGraph. Keep `Task`'s dependency and
source-order-index contract stable.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
