# S01 — Benchmark harness (cobra-bench v0)

| Field | Value |
|---|---|
| Milestone | M0 — Thesis validation |
| Depends on | S00 (done) |
| Hardware | CPU-only (GPU metadata paths guarded, tested with fakes) |
| Estimated sessions | 2-3 |
| Plan sections | §20.5, §20.7, §33 (all), §34.9 |

## Objective

Build the measurement instrument BEFORE any optimization exists (plan
Phase 0 principle: "benchmark infrastructure before building a large
compiler"). Deliver a Python package + `cobra-bench` CLI implementing the
§33 runbook: manifests, machine metadata capture, the timing protocol,
bootstrap statistics, and correctness-gated measurement.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §20.5 (timing protocol), §20.7 (stats),
   §33.1-33.11 (runbook: manifest, host prep, schema, anti-patterns)
3. `benchmarks/` READMEs from S00

## Out of scope

- Real workloads (S02). Nsight integration beyond invoking `nsys` if
  present (S02). B2 hand-tuned baselines. `cobra-bench compare` release
  policies (S28 refines).

## Tasks

### T1 — Package + manifest schema
- [ ] Do: `benchmarks/harness/` as installable module `cobra_bench`
  (wired into the uv workspace). Implement the §33.1 manifest as typed
  dataclasses + YAML loader with validation. Hand-entered fields must be
  explicitly marked `manual: true` and are rejected by default in strict
  mode (§33.1 last paragraph).
- Accept: invalid manifests fail with field-level errors; example
  manifest in `benchmarks/suites/example.yaml` round-trips.

### T2 — Machine metadata collector (`cobra-bench doctor`)
- [ ] Do: capture OS/kernel/CPU/NUMA/RAM; GPU via `nvidia-smi` (name,
  driver, clocks policy, power limit, persistence, MIG) when present;
  Python/framework versions via importlib. Output
  `artifacts/environment.json`. `--strict` fails when required fields are
  missing (per §33.2). All collectors unit-tested with fakes so CI (no
  GPU) stays green.
- Accept: runs on a GPU-less machine with clear "gpu: absent"; strict
  mode exits nonzero there.

### T3 — Timing protocol engine
- [ ] Do: implement §20.5 + §33.5/33.6: warmup-until-stable policy (min
  count, median band, max cap reported as failure), ≥30 samples default,
  randomized variant order, cold mode = process-per-sample (subprocess),
  per-sample correctness hook — a failed oracle invalidates that
  variant's timings (§33.4). CUDA sync points are pluggable callables so
  the engine stays framework-agnostic.
- Accept: deterministic-fake-clock unit tests cover: stability stop,
  max-warmup failure, order randomization, correctness-gating.

### T4 — Result schema + statistics
- [ ] Do: per-sample record per §33.10 (distinguish real-zero from
  unavailable via `null`), written as JSON-lines + Parquet (pyarrow).
  `cobra-bench analyze`: median, p95/p99, geometric-mean speedup,
  bootstrap 95% CI, coefficient of variation; outputs `summary.md`,
  `summary.json`, `confidence_intervals.csv` (§33.8). A speedup is
  labeled `significant` only when the CI excludes 1.0x (§20.7).
- Accept: stats unit-tested against known distributions (seeded); CI
  bounds match a reference implementation within tolerance.

### T5 — CLI assembly
- [ ] Do: `cobra-bench` entry point with `doctor | verify | run |
  analyze | compare` (§33 command shapes; `verify` runs oracles only,
  `compare` v0 = threshold check between two summary.json files).
  `--output` directory convention `artifacts/…` per runbook.
- Accept: `cobra-bench run --suite benchmarks/suites/example.yaml
  --variants a,b --phase warm` measures two dummy Python workloads
  end-to-end and `analyze` produces the artifact set.

### T6 — Anti-pattern guardrails
- [ ] Do: encode §33.11 as automated checks where possible: refuse mixed
  cold/warm comparison, refuse comparing variants with different input
  fingerprints, warn when sample count <30, refuse timing when the
  correctness hook is absent (must be explicit `--no-oracle` with a
  loud warning).
- Accept: each guardrail has a unit test proving it triggers.

## Validation

```bash
uv run pytest benchmarks/harness -q
uv run cobra-bench doctor --output /tmp/env.json
uv run cobra-bench run --suite benchmarks/suites/example.yaml \
  --variants a,b --phase warm --output /tmp/bench
uv run cobra-bench analyze --input /tmp/bench --output /tmp/analysis
test -f /tmp/analysis/summary.json
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; validation green from clean checkout
- [ ] Harness has zero dependencies on Cobra internals (it must be able to
      measure ANY Python callable — it outlives prototypes)
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S02 defines real workloads as suite YAMLs + workload modules consumed by
this harness; S02 runs on the GPU host — its executor must record host
details into STATE.md Environment.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
