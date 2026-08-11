# S23 — Optimizer passes (parallelize / fuse / place)

| Field | Value |
|---|---|
| GitHub issue | #24 |
| Milestone | M4 — v0.1 hardening & release |
| Depends on | S22 (done) |
| Hardware | **NVIDIA GPU required** (mechanism verification) |
| Estimated sessions | 3 |
| Plan sections | §8.5, §8.6, §10.3 (safe subset), §35 Epic 9, §18.1, §21.4 |

## Objective

Assemble the v0.1 optimizer as disciplined MLIR passes: auto-parallel
region discovery on S22's legality, hardened fusion/coarsening, hardened
transfer elimination, EFT placement with bounded local search — every
pass flag-gated, diagnosable, and covered by positive AND
legality-negative tests. This is where the §18.1 nine-point checklist
becomes muscle memory.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §8.5 (algorithm), §8.6 (granularity),
   §10.3 (relational optimizations — safe subset), §18.1 (TDD contract
   per optimization), §21.4 (feature-flag requirements)
3. `lib/Analysis/` interfaces (S22), cost model API (S19), S15
   calibration/coarsening

## Out of scope

- New backends, Triton codegen, autotuning. Multi-GPU placement.
  Relational join-strategy selection + aggregate partialization (§10.3
  advanced rows — beta). Anything without a benchmark hypothesis.

## Tasks

Every task follows §18.1: contract → failing test → impl → differential
→ IR regression → benchmark hypothesis + measurement → flag + docs.

### T1 — Auto-parallel discovery pass
- [ ] Do: `--cobra-parallelize`: identify independent regions via S22
  effects/aliases; insert fork/join; respect §8.5 constraint list
  (deps, effects, aliases, exceptions, benefit>overhead via S19 model,
  resource budgets). Negative tests: shared-mutable-state, ordered-IO,
  RNG-shared, uncertain-alias — must NOT transform (the §34.5 dual-RUN
  pattern with SAFE prefix).
- Accept: lit positive+negative; differential corpus stays green with
  pass ON; `model_ensemble` still overlaps (now discovered, not
  hand-wired).

### T2 — Fusion & coarsening pass hardened
- [ ] Do: promote S15's coarsening v0 into `--cobra-coarsen` with
  effect-legality (never fuse across barriers), min-cost threshold from
  calibration, batching of homogeneous small tasks (§8.6); relational
  projection-pruning + filter/projection fusion where §10.3-safe.
- Accept: lit tests incl. barrier-blocks-fusion negatives; 1000-node
  chain benchmark shows scheduling overhead drop (hypothesis +
  measurement in Session log).

### T3 — Transfer elimination hardened + placement v1
- [ ] Do: extend S19-T3: residency propagation across rel→tensor
  boundaries, redundant round-trip removal verified by S18 counters;
  placement upgraded to full §8.5 EFT + memory penalty + uncertainty
  penalty + bounded local search (step 7), deterministic output.
- Accept: lit + counter-verified integration tests;
  `parquet_feature_inference` h2d bytes reduction vs pass-off recorded
  (feeds the §24.2 "30% bytes reduction on ≥2 pipelines" gate — check
  status honestly in Session log).

### T4 — Pass pipeline + flags + diagnostics
- [ ] Do: assemble `cobra-default-pipeline` (canonicalize → effects →
  parallelize → coarsen → transfer-elim → place → schedule-emit);
  every pass: global flag, per-region disable where practical,
  diagnostic ID, counters (§21.4); `cobra explain` renders which passes
  fired and why per region.
- Accept: pipeline reproducible (same IR in → same IR out, test);
  flags round-trip through config precedence (§17.3, basic impl);
  explain snapshot shows pass attribution.

### T5 — Optimizer-on soak of the corpus
- [ ] Do: run the FULL differential corpus + workload oracles with the
  complete pipeline enabled, plus shadow mode spot-checks; fix or
  file-and-flag-off any divergence (wrong-code policy §18.5 — default
  OFF until fixed).
- Accept: corpus green with pipeline ON; zero known wrong-code with
  any default-enabled pass.

## Validation

```bash
cmake --build --preset dev --target check-cobra-lit
uv run pytest test/Differential -q                    # pipeline ON (default)
COBRA_DISABLE_OPTIMIZER=1 uv run pytest test/Differential -q   # and OFF
uv run pytest test/python/test_pass_flags.py -q
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted (Epic 9 acceptance: never parallelizes known
      conflicts, rejects unprofitable, explain shows costs, mechanisms
      visible in IR)
- [ ] Every pass documented in `docs/reference/passes.md` (flag, ID,
      legality summary, rollback)
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S24 grows the corpus against THIS pipeline. S26 exposes the flags via
config/CLI. Any pass found unsafe later gets flag-disabled first, fixed
second (§18.5).

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
