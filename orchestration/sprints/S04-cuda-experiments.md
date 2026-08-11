# S04 — CUDA experiments A/B/C (the three high-risk bets)

| Field | Value |
|---|---|
| GitHub issue | #5 |
| Milestone | M0 — Thesis validation |
| Depends on | S03 (done) |
| Hardware | **NVIDIA GPU required** |
| Estimated sessions | 2-4 |
| Plan sections | §29 (Days 21-30), §12.3-12.4, §11.1-11.2, §20.5, §33.7 |

## Objective

Run the three experiments that decide whether Cobra deserves to exist
(§29 Days 21-30). Each is a hand-built prototype of one optimization
mechanism, measured against B1 with full statistical rigor. These are
prototypes, not products — but their MEASUREMENTS must be
release-quality.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §29 Days 21-30, §12.4 (CUDA Graphs
   eligibility), §11.1-11.2 (DLPack/Arrow boundaries), §33.7 (profiler
   evidence requirement)
3. `docs/benchmarks/phase0-tracer-findings.md` (S03), S02 workload code
4. `docs/benchmarks/phase0-baseline.md` (the B1 numbers to beat)

## Out of scope

- Generalizing any experiment into reusable infrastructure (that is M1+).
- New workloads. Multi-GPU. Training.

## Tasks

Each experiment follows the same contract (plan §18.2): write
`experimental/experiments/<X>/HYPOTHESIS.md` FIRST (claim, mechanism,
expected %, rollback), then implement, then measure via cobra-bench
(≥30 warm samples, correctness-gated), then write `RESULTS.md` with CI,
profiler trace refs, and an honest verdict.

### T1 — Experiment A: parallel branch overlap
- [ ] Do: `model_ensemble` with the two branches issued on separate
  `torch.cuda.Stream`s with event-based joins; validate outputs equal
  sequential run; verify exception behavior (inject a failing branch;
  earliest-source-order exception must surface — charter/§8.3). Measure
  wall latency vs B1; capture nsys trace showing actual kernel overlap.
- Accept: RESULTS.md with CI-bounded speedup (or honest negative), a
  trace screenshot/ref proving overlap or explaining its absence
  (occupancy?), and exception-semantics test passing.

### T2 — Experiment B: dataframe→tensor residency
- [ ] Do: `parquet_feature_inference` variant where preprocessing runs in
  cuDF and hands off to torch via DLPack (or Arrow C Device) WITHOUT a
  host round-trip. Count h2d/d2h bytes (nsys or torch profiler memory
  events) for: pandas→numpy→torch path vs cuDF→DLPack path. Validate
  output parity within the workload oracle.
- Accept: RESULTS.md with transfer-byte table + latency CI; explicit
  documentation of any semantic hazards hit (nulls, categoricals,
  index) and how they were detected.

### T3 — Experiment C: CUDA Graph replay economics
- [ ] Do: capture the repeated inference region of
  `cv_preprocess_inference_postprocess` (or `model_ensemble` if shapes
  are more stable) with `torch.cuda.graphs`; measure warm replay vs
  non-graph execution: latency, launch count (nsys), and break-even
  iteration count (§13.4 formula).
- Accept: RESULTS.md with launch-count reduction, replay speedup CI, and
  computed break-even.

### T4 — Consolidated Phase-0 evidence memo
- [ ] Do: `docs/benchmarks/phase0-experiments.md`: table of the three
  experiments vs the S05 gate bar (≥15% over B1, statistically valid, on
  ≥1 experiment), mechanisms proven, mechanisms disproven, and the
  honest list of caveats. Every claimed win must reference its trace
  file (§33.7).
- Accept: memo complete; a skeptical reader can reproduce every number
  via a listed command.

## Validation

```bash
uv run pytest experimental/experiments -q          # correctness harnesses
ls experimental/experiments/*/HYPOTHESIS.md | wc -l   # == 3
ls experimental/experiments/*/RESULTS.md | wc -l      # == 3
test -f docs/benchmarks/phase0-experiments.md
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; every RESULTS.md has: CI, oracle status,
      trace reference, verdict (no vibes)
- [ ] Negative results reported as prominently as wins (§20.10 spirit)
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S05 is the day-30 gate: it consumes `phase0-experiments.md`,
`phase0-tracer-findings.md`, `phase0-baseline.md`, and ADR-0005 (charter
draft). Nothing else is needed — make those four documents airtight.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
