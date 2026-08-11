# S19 — Cost model v0, profitability gate, CUDA Graphs

| Field | Value |
|---|---|
| GitHub issue | #20 |
| Milestone | M3 — Integration & evidence |
| Depends on | S15, S18 (done) |
| Hardware | **NVIDIA GPU required** |
| Estimated sessions | 3 |
| Plan sections | §13.1-13.4, §12.4, §8.5 (inputs), §35 Epics 9-10 (v0.1 subset) |

## Objective

Give Cobra judgment: an analytical cost model fed by S15 calibration,
a profitability gate that REFUSES unprofitable plans (§13.4), first
optimization passes (transfer elimination, placement v0), and CUDA
Graph capture for stable repeated regions. After this sprint Cobra can
decline to optimize — which the plan treats as a feature, not a bug.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §13.1 (inputs), §13.2 v0.1 stage, §13.4
   (gate formula), §12.4 (CUDA Graph eligibility + reporting), §8.5
   (planner integration points)
3. `calibration.json` schema (S15), copy counters (S18), scheduler
   annotations (S13)

## Out of scope

- Autotuning beyond `off` (§13.3 — bounded benchmarking is beta).
  Learned cost models (v1). Multi-GPU placement (beta). Triton kernel
  generation (post-v0.1 unless S21 decides otherwise — vendor/Inductor
  dispatch only, §9.4 order 1-2).

## Tasks

### T1 — Cost model v0
- [ ] Do: `lib/Analysis/CostModel/`: per-node estimates from §13.1
  inputs: op class + sizes → FLOPs/bytes heuristics; transfer cost =
  size/curve(calibration); launch + scheduling overhead from
  calibration; uncertainty score per estimate (wide for opaque nodes);
  observed-runtime correction store (per cache key, updates estimates
  after real runs — §13.2 v0.1 line 4).
- Accept: unit tests with synthetic calibrations; estimates for the
  three workloads within documented sanity bounds of measured reality
  (assert order-of-magnitude, not precision).

### T2 — Profitability gate + break-even reporting
- [ ] Do: implement §13.4: plan installed only when expected gain >
  compile amortization + scheduling overhead + transfer cost +
  uncertainty margin; compute `break_even_runs` (§20.8) per plan;
  explain + `cobra benchmark` render it; rejected plans run the
  strongest fallback and log `GB-UNPROFITABLE` with the numbers.
- Accept: test — a tiny workload (below S15's minimum profitable task
  size) is REJECTED and runs eager; a large one is accepted; break-even
  appears in explain JSON.

### T3 — Transfer elimination + placement v0 passes
- [ ] Do: MLIR passes: (a) transfer elimination — remove redundant
  h2d/d2h pairs, keep values device-resident when consumer is on-device
  (verified against S18 counters); (b) placement v0 — EFT-based device
  assignment (host CPU vs GPU0) using T1 costs, GPU-affinity bonus for
  values feeding GPU models (§10.2). Both passes flag-gated with
  positive AND legality-negative lit tests (§19.4).
- Accept: `parquet_feature_inference` IR after passes shows eliminated
  transfers (FileCheck) AND runtime counters confirm the reduction
  (integration test: bytes drop vs passes-off run).

### T4 — CUDA Graph capture/replay
- [ ] Do: eligibility detection per §12.4 (stable shapes via guards, no
  unsupported ops inside, stable memory via S14 pool reservation);
  `cobra.schedule`-level graph-capture node (introduce the minimal
  `cobra.schedule` ops needed: launch/capture/replay); capture on
  first eligible warm run, replay after; invalidation on guard change;
  report eligibility/failures/replay-count/savings (§12.4 reporting
  list) through explain.
- Accept: repeated-inference test — replay reduces launch count
  (nsys/counter evidence) and wall time; a shape change invalidates and
  recaptures exactly once; ineligible region (has fallback node) is
  refused with a reported reason.

### T5 — Plan cache integration
- [ ] Do: cost-model version + calibration fingerprint join the S11
  cache key (fields were reserved); cached plans store estimated +
  last-observed costs; explain shows estimated-vs-observed drift.
- Accept: calibration change → cache miss (test); drift >2x logs a
  correction event (test with fake observation).

## Validation

```bash
cmake --build --preset dev --target check-cobra-lit   # pass tests
uv run pytest test/python/test_profitability.py test/python/test_cudagraphs.py -q
uv run python examples/profitability_demo.py           # shows accept + reject cases
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted (Epic 9: no known-conflict parallelization,
      unprofitable rejected, explain shows est+observed; Epic 10:
      replay correct, invalidation works, vendor dispatch preferred)
- [ ] Every new pass has a feature flag + diagnostic ID (§21.4)
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S20 runs the full B0-B3 evidence package using everything since S16.
The B3 variant is now: capture + placement + transfer elimination +
overlap + CUDA Graphs, all behind their flags (S20 documents the exact
flag set as the "release-default safe configuration", §20.2).

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
