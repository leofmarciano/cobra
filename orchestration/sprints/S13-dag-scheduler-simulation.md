# S13 — DAG scheduler + virtual-clock simulation

| Field | Value |
|---|---|
| GitHub issue | #14 |
| Milestone | M2 — Runtime & scheduler |
| Depends on | S08 (done); S12 merged (WIP order) |
| Hardware | CPU-only |
| Estimated sessions | 2-3 |
| Plan sections | §8.5, §8.6, §8.3, §12.6, §19.12 |

## Objective

Build the scheduling POLICY layer on top of the S08 executor: v0.1
planner (earliest-finish-time with transfer costs), deterministic mode,
and — critically — the virtual-clock simulation harness that lets us
test scheduling exhaustively without hardware (§19.12: "the virtual
scheduler is used for exhaustive small-DAG exploration").

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §8.5 (planner inputs + algorithm +
   pseudocode), §8.6 (granularity mechanisms), §8.3 (exception policy),
   §12.6 (cancellation), §19.12 (required simulation cases)
3. `include/cobra/runtime/` headers (S08)

## Out of scope

- Real CUDA (S14 — this sprint's "devices" are fakes with declared
  costs/latencies). Cost MODEL (S19 — here costs are given inputs).
  Multi-GPU policy (beta). Calibration (S15).

## Tasks

### T1 — Scheduler core (policy over mechanism)
- [ ] Do: `runtime/core/scheduler/`: node annotations (candidate
  devices, est. compute cost per device, input/output sizes, transfer
  cost fn, memory demand, effect constraints, source-order index,
  critical-path distance); implement §8.5 algorithm steps 1-8: validate
  → fuse-eligible marking (hook only) → critical path → prune illegal
  placements → EFT assignment with transfer costs → readiness priority
  by CP-distance + memory pressure → bounded local search → emit
  deterministic `Schedule` object.
- Accept: unit tests on hand-computed small DAGs verify EFT choices and
  determinism (same input → identical schedule, 100 runs).

### T2 — Virtual-clock simulation harness
- [ ] Do: `test/Runtime/sim/`: fake devices (configurable concurrency,
  transfer bandwidth, failure/latency injection), virtual clock, script
  runner that executes a `Schedule` in simulated time and records a
  timeline. Assertion helpers: makespan, ordering, overlap, resource
  bounds.
- Accept: harness itself unit-tested (a known 3-node plan produces the
  hand-computed timeline).

### T3 — §19.12 case suite
- [ ] Do: implement the full §19.12 list as simulation tests (single-GPU
  scope): one chain; wide fan-out/fan-in; mixed CPU+GPU nodes; transfer
  overlap; memory-pressure backoff; resource starvation; failed-node
  propagation; cancellation; timeout; stream exhaustion; device loss;
  OOM retry policy hook; deterministic mode; priority-inversion
  prevention. (Multi-GPU + NCCL rows are beta — mark skipped with
  reason.)
- Accept: every listed case has a test; failures produce readable
  timeline dumps.

### T4 — Exhaustive small-DAG exploration
- [ ] Do: property-style test enumerating all DAG shapes ≤6 nodes with
  random effect/cost assignments (seeded): invariants — no conflicting
  effects overlap, data deps respected, exception winner is earliest
  source-order, cancellation never loses the selected exception, memory
  cap never exceeded.
- Accept: 10k seeded cases pass in CI time budget; failures shrink to a
  minimal DAG and persist as fixtures.

### T5 — Deterministic mode + schedule dump
- [ ] Do: `deterministic` flag → stable tie-breaking (source order) and
  serialized schedule output (JSON) for explain/debugging; document in
  `docs/reference/schedule-format.md`.
- Accept: deterministic runs produce byte-identical schedule dumps.

## Validation

```bash
cmake --build --preset dev --target check-cobra-unit
ctest --preset tsan -R scheduler
uv run pytest test/Runtime/sim -q     # if harness is driven from Python
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; §19.12 single-GPU rows all covered; TSan green
- [ ] Schedule format documented + versioned
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S14 binds real CUDA streams/events to the `Schedule` contract (the sim
fake-device API is the spec). S19's cost model fills the annotation
inputs this scheduler consumes.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
