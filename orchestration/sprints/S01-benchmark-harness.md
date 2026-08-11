# S01 — Benchmark harness (cobra-bench v0)

| Field | Value |
|---|---|
| GitHub issue | #2 |
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
- [x] Do: `benchmarks/harness/` as installable module `cobra_bench`
  (wired into the uv workspace). Implement the §33.1 manifest as typed
  dataclasses + YAML loader with validation. Hand-entered fields must be
  explicitly marked `manual: true` and are rejected by default in strict
  mode (§33.1 last paragraph).
- Accept: invalid manifests fail with field-level errors; example
  manifest in `benchmarks/suites/example.yaml` round-trips.

### T2 — Machine metadata collector (`cobra-bench doctor`)
- [x] Do: capture OS/kernel/CPU/NUMA/RAM; GPU via `nvidia-smi` (name,
  driver, clocks policy, power limit, persistence, MIG) when present;
  Python/framework versions via importlib. Output
  `artifacts/environment.json`. `--strict` fails when required fields are
  missing (per §33.2). All collectors unit-tested with fakes so CI (no
  GPU) stays green.
- Accept: runs on a GPU-less machine with clear "gpu: absent"; strict
  mode exits nonzero there.

### T3 — Timing protocol engine
- [x] Do: implement §20.5 + §33.5/33.6: warmup-until-stable policy (min
  count, median band, max cap reported as failure), ≥30 samples default,
  randomized variant order, cold mode = process-per-sample (subprocess),
  per-sample correctness hook — a failed oracle invalidates that
  variant's timings (§33.4). CUDA sync points are pluggable callables so
  the engine stays framework-agnostic.
- Accept: deterministic-fake-clock unit tests cover: stability stop,
  max-warmup failure, order randomization, correctness-gating.

### T4 — Result schema + statistics
- [x] Do: per-sample record per §33.10 (distinguish real-zero from
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
- [2026-08-11][S01 executor (P0), T1] Done: created `benchmarks/harness/`
  as a `uv` workspace member package `cobra-bench` (src layout,
  `pyproject.toml`, added to root `[tool.uv.workspace]` +
  `[tool.uv.sources]`, and to the root dev dependency group so `uv sync`
  installs it editable). Implemented `cobra_bench.manifest`: dataclasses
  for the §33.1 manifest (host/cuda/software/protocol/correctness sections
  + workload/variant lists), a hand-written field-level validator
  (`manifest_from_dict`/`load_manifest`, raising `ManifestError` with all
  problems collected, not just the first), `manifest_to_dict`/
  `dump_manifest` for round-tripping, and strict-mode rejection of any
  section marked `manual: true` per the §33.1 last paragraph. Added
  `benchmarks/suites/example.yaml` (two dummy Python variants under
  `cobra_bench.examples.dummy`, reusable by T5) and
  `benchmarks/harness/tests/test_manifest.py` (11 cases: load, round-trip,
  missing/wrong-type/unknown-field errors, multi-error aggregation,
  manual/strict interaction, invalid entrypoint format, protocol
  defaults) — written before the implementation (TDD). Added
  `pyyaml` (harness runtime dep) and `types-pyyaml` (root dev dep, for
  `mypy --strict` on `cobra_bench`, verified separately from `./scripts/check.sh`
  since mypy in CI is currently scoped to `cobra_compiler` only). Recorded
  in `orchestration/DECISIONS.md` (D-005).
  Validation: `uv run pytest benchmarks/harness -q` (11 passed),
  `uv run mypy benchmarks/harness/src/cobra_bench --strict` (clean),
  `./scripts/check.sh` (all green).
  Next: T2 — machine metadata collector (`cobra-bench doctor`).
  Surprises: a naive dict-pop validator silently left `None`-valued keys
  in the "remaining" dict, causing false "unknown field" errors on
  legitimately-null optional fields (e.g. `container_digest: null`) —
  fixed by always popping the key even when short-circuiting on `None`.
  Also: PyYAML's default loader parses unquoted all-digit strings (e.g. a
  40-char all-zero commit hash) as `int`; the example manifest now quotes
  `commit`/`workload_commit` explicitly — worth a LEARNINGS note for
  anyone hand-writing suite YAML with hash-like fields.
- [2026-08-11][S01 recovery (P2)] RECOVERY:
  - Found `sprint/S01-benchmark-harness` with T1 (b32b7e3) and T2 (e074718)
    already committed, but T2 handoff was not recorded. T3 was fully staged
    but not committed.
  - Also in the working tree: an unrelated, half-finished
    `scripts/cobra_orca_loop.py` change (advisory `fcntl` lock) that failed
    `ruff B904`, plus an untracked `scripts/.cobra_loop.lock`.
  - T3 verified: `uv run pytest benchmarks/harness -q` (56 passed),
    `uv run mypy benchmarks/harness/src/cobra_bench --strict` (clean),
    `ruff check` / `ruff format --check` on `benchmarks/harness` (clean).
    Committed to the sprint branch as
    `S01: recovered work-in-progress (T3 timing protocol engine)`.
  - Rescued the broken loop-harness WIP to `rescue/S01-2026-08-11`; reverted
    `scripts/cobra_orca_loop.py` on the sprint branch and removed
    `scripts/.cobra_loop.lock`. Working tree is now clean.
  - STATE.md corrected to current task T4. Next: T4 — result schema +
    statistics.
- [2026-08-11][S01 executor (P0), T4] Done: implemented `cobra_bench.results`
  (`SampleRecord` per §33.10 with optional fields to distinguish real-zero
  from unavailable, JSON-lines and Parquet read/write), `cobra_bench.stats`
  (median, p95/p99, geometric mean, coefficient of variation, bootstrap-95%
  CI for both raw metric and baseline-relative speedup, significance when the
  CI excludes 1.0x per §20.7), and `cobra_bench.analyze` + the unified
  `cobra-bench` CLI entry point with the `analyze` subcommand. Added
  `pyarrow>=19.0,<20` runtime dependency (recorded in `DECISIONS.md` as
  D-006) and harness-local `[tool.mypy]` overrides for untyped pyarrow
  imports. Generated artifacts: `summary.md`, `summary.json`, and
  `confidence_intervals.csv`. Added 30 new TDD unit tests across
  `test_results.py`, `test_stats.py`, and `test_analyze.py`. Validation:
  `uv run pytest benchmarks/harness -q` (86 passed),
  `uv run mypy benchmarks/harness/src/cobra_bench --strict` (clean),
  `uv run ruff check benchmarks/harness` and `ruff format --check` (clean),
  `./scripts/check.sh` (green). T4 checked; sprint `in_progress`; next is
  T5 — CLI assembly (`doctor|verify|run|analyze|compare` and end-to-end
  `cobra-bench run` with the example suite).
