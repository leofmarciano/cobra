# S20 — Day-90 evidence package (B0-B3)

| Field | Value |
|---|---|
| Milestone | M3 — Integration & evidence |
| Depends on | S19 (done) |
| Hardware | **NVIDIA GPU required** (frozen bench host only) |
| Estimated sessions | 2 |
| Plan sections | §29 (Days 76-90), §20.2, §33 (full runbook), §27.4 |

## Objective

Produce the integrated, reproducible evidence package the day-90 gate
judges: B0-B3 on all three workloads with the full §33 protocol,
profiler traces mapping every gain to a mechanism, and an honest
internal report including failures and limitations. This is also the
dry run of the §27.4 "what to show NVIDIA" package format.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §20.2 (baseline definitions), §33.5-33.12
   (measurement + report requirements), §29 Days 76-90
3. `benchmarks/suites/phase0.yaml` (S02 — extend, don't regenerate
   datasets), S19's flag documentation

## Out of scope

- New features or fixes beyond measurement-blocking bugs (anything else
  found → Session log + STATE notes for post-gate). B2 for all three
  workloads is NICE-to-have; required for at least ONE workload (pick
  the one with the clearest hand-tuned pattern, likely
  `model_ensemble` with manual streams from Experiment A).

## Tasks

### T1 — B3 variant + release-default config
- [ ] Do: define B3 = `@cobra.compile` with the safe default flag set
  (document exactly which optimizations are on: capture, effects-aware
  overlap, placement v0, transfer elimination, CUDA Graphs where
  eligible; math=strict); commit as
  `docs/reference/v0.1-default-config.md`; wire b3 into the suite for
  all three workloads.
- Accept: b3 passes `cobra-bench verify` (oracles) on all workloads.

### T2 — B2 hand-tuned reference (≥1 workload)
- [ ] Do: adapt Experiment A's manual-streams implementation into a
  maintained B2 variant for `model_ensemble` (explicit streams +
  torch.compile + manual transfer placement, §20.2 B2 definition);
  document the engineering time it represents.
- Accept: b2 verified + measured; documented in the suite YAML.

### T3 — Full measurement campaign
- [ ] Do: on the frozen host (§33.2 prep + doctor strict): cold + warm
  phases, ≥30 samples, randomized order, per-sample oracles, for
  B0/B1/B3 (+B2 where present) × 3 workloads; nsys traces for B1 vs B3
  on every workload (§33.7); collect S18 transfer counters + launch
  counts + break-even numbers (§20.8) into the result records.
- Accept: raw artifacts + analysis outputs committed under
  `artifacts/{raw,analysis}/day90/`; no §33.11 anti-pattern (validator
  hunts).

### T4 — Internal report
- [ ] Do: `docs/benchmarks/day90-report.md` answering all §33.12
  questions: exact environment, baseline configs, unsupported cases,
  cold/warm separation, oracle methodology, CIs, mechanism per gain
  (trace refs), compile time + break-even, memory/transfer deltas,
  regressions, reproduction commands. Include the honest-failures
  section prominently (§20.10).
- Accept: an engineer outside the loop could reproduce every headline
  number from the report alone (validator simulates this).

### T5 — Gate-readiness self-check
- [ ] Do: pre-compute the S21 checklist values: capture % of runtime
  weight per workload (from explain node accounting), best speedup vs
  B1 with CI, transfer-boundary eliminations, scheduler overhead vs
  gains; write them into the report's final table.
- Accept: table complete with evidence links; no value left "TBD".

## Validation

```bash
uv run cobra-bench verify --suite benchmarks/suites/day90.yaml --variants b0,b1,b2,b3
uv run cobra-bench run --suite benchmarks/suites/day90.yaml \
  --variants b0,b1,b3 --phase warm --output artifacts/raw/day90
uv run cobra-bench analyze --input artifacts/raw/day90 --output artifacts/analysis/day90
test -f docs/benchmarks/day90-report.md
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; report + raw data + traces committed
- [ ] Every speedup claim: oracle-passed, CI-bounded, mechanism-traced
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S21 (gate) consumes `day90-report.md` + artifacts. Nothing else. If a
gate criterion is obviously unmet, S20's Session log must say so plainly
— surprising the gate is a process failure.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
