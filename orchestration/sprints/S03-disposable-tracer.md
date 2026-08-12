# S03 — Disposable whole-program tracer

| Field | Value |
|---|---|
| GitHub issue | #4 |
| Milestone | M0 — Thesis validation |
| Depends on | S02 (done) |
| Hardware | **NVIDIA GPU required** (traces the real workloads) |
| Estimated sessions | 2 |
| Plan sections | §29 (Days 11-20), §5.2, §6.1-6.2 |

## Objective

Build the throwaway tracer that proves we can SEE the program: record
call boundaries, tensor/dataframe metadata, dependencies, and timings for
the three frozen workloads; render the program DAG; compute critical path
and available parallelism. This de-risks the capture thesis before any
compiler exists. **This code is explicitly disposable** — it lives in
`experimental/` and never enters a release path (plan §18.4).

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §29 Days 11-20, §6.1 (capture flow),
   §6.2 (capture levels)
3. Workload modules from S02 (`benchmarks/pipelines/`)

## Out of scope

- Guards, caching, IR, correctness of parallel EXECUTION (S04) — this
  sprint only OBSERVES. Perfect Python coverage — unknown calls are
  recorded as opaque nodes, that is fine.

## Tasks

### T1 — Call-boundary recorder
- [x] Do: `experimental/tracer/` package. Record torch ops via
  `__torch_function__`/`TorchFunctionMode`; pandas via method
  wrapping of a supported-op list (§10.1 names); numpy via
  `__array_function__`; everything else via an explicit opaque-node
  wrapper. Each event: op name, args summary, tensor/df metadata (dtype,
  shape/schema, device, storage id), wall time, thread id, source
  location (`inspect`).
- Accept: tracing `model_ensemble` yields events for both model branches
  with distinct storage lineages; overhead <10x eager (it's a tracer,
  not a product — just don't make it useless).

### T2 — Dependency DAG builder
- [x] Do: connect events into a DAG via value identity (tensor storage,
  df object id, opaque handles). Unknown-effect nodes get ordering edges
  to neighbors (conservative, §6.3 spirit). Export JSON + Graphviz dot.
- Accept: unit tests on synthetic event streams: chain, fan-out/fan-in,
  mutation-forces-ordering.

### T3 — Critical path & parallelism analysis
- [x] Do: from recorded wall times: critical-path length, total work,
  max theoretical speedup (work/span), device residency timeline
  (which values bounce host↔device and when), transfer count estimate.
  Emit `experimental/tracer/reports/<workload>.md` + rendered DAG.
- [x] Accept: three workload reports exist with: span/work ratio, top-5
  critical-path ops, observed transfer boundaries, and candidate
  parallel regions (named).

### T4 — Findings memo
- [x] Do: `docs/benchmarks/phase0-tracer-findings.md` — for each
  workload: the 2-3 concrete optimization opportunities visible in the
  DAG (e.g., "branches A/B independent: 41% span reduction if
  overlapped"; "df→tensor crosses host needlessly"). Explicitly mark
  which opportunities a tensor-only compiler (torch.compile alone)
  CANNOT see — this feeds the S05 gate criterion.
- [x] Accept: memo lists ≥2 cross-library opportunities total, each with a
  quantified estimate from trace data.

## Validation

```bash
uv run pytest experimental/tracer -q
uv run python -m tracer.run --workload all --out experimental/tracer/reports/
ls experimental/tracer/reports/*.md | wc -l   # == 3
test -f docs/benchmarks/phase0-tracer-findings.md
./scripts/check.sh
```

## Definition of Done

- [x] All tasks accepted; three reports + findings memo committed
- [x] `experimental/tracer/README.md` opens with "DISPOSABLE — not
      release code" (plan §18.4)
- [x] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S04 implements the three §29 experiments against the opportunities this
memo identified. S10 later converts tracer JSON into real Cobra IR — keep
the JSON schema documented in the tracer README.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->

- [2026-08-11][executor P0] T1 done. Added `experimental/tracer/` as a uv
  workspace member (`cobra-tracer`, `src/tracer/` layout) with:
  `events.py` (Event schema), `handles.py` (value-identity handles keyed by
  tensor storage pointer / dataframe object id / ndarray base id — views
  share a handle), `metadata.py` (dtype/shape/schema/device capture),
  `session.py` (TraceSession + `trace()` context manager wiring all
  recorders), `torch_mode.py` (real `TorchFunctionMode`),
  `pandas_wrap.py` (method wrapping over the plan §10.1 op list, restored
  on exit), `numpy_wrap.py` (real `__array_function__` dispatch on a
  `TracedArray` subclass — tracing propagates through chained numpy calls
  since results are re-wrapped), `opaque.py` (decorator + `call_opaque`
  wrapper with conservative `"opaque:"`-prefixed op names).
  19 unit/integration tests in `experimental/tracer/tests/` pass
  (`uv run pytest experimental/tracer -q`), including the T1 acceptance
  criterion directly: tracing a `model_ensemble`-shaped dual-branch
  pipeline yields events for both branches with disjoint output handles
  (`test_session_integration.py`). Also manually traced the real
  `cobra_pipelines.model_ensemble.b0()` workload: 510 torch events
  recorded, traced wall time was *not* slower than eager (well under the
  10x budget) once `_source_location` stopped calling
  `Path.resolve()`/`os.path.abspath()` per recorded event (that made a
  synthetic 50-iteration microbenchmark ~250x slower — see
  `orchestration/LEARNINGS.md`). `./scripts/check.sh` passes.
  Next: T2 (dependency DAG builder — connect `session.events` into a DAG
  via the `input_handles`/`output_handles` already recorded, with
  conservative ordering edges for opaque nodes; export JSON + Graphviz
  dot; unit tests on synthetic event streams for chain / fan-out-fan-in /
  mutation-forces-ordering). Sprint remains `in_progress`.

- [2026-08-11][executor P0] T2 done. Added `experimental/tracer/src/tracer/dag.py`
  (`build_dag`, `to_json`, `to_dot`): builds a DAG from recorded `Event`s by
  value-identity handle, emitting `data` edges from the last producer of a
  handle to its consumers and `order` edges between successive producers of
  the same handle (mutation ordering). Opaque nodes receive conservative
  program-order `order` edges to their immediate neighbors (plan §6.3
  spirit). Exports JSON and Graphviz DOT with shape/color hints per
  recorder kind. Added 7 unit tests in `experimental/tracer/tests/test_dag.py`
  covering chain, fan-out/fan-in, mutation-forces-ordering, opaque
  neighbor fencing, isolated roots/leaves, and JSON/DOT export.
  Updated `tracer/__init__.py` to expose the new functions and documented
  the JSON schema in `experimental/tracer/README.md`. Tracer suite now
  passes 26 tests (`uv run pytest experimental/tracer -q`); `./scripts/check.sh`
  passes. Next: T3 (critical path / parallelism analysis + reports for the
  three workloads). Sprint remains `in_progress`.

- [2026-08-11][executor P0] T3 and T4 done. Added
  `experimental/tracer/src/tracer/analysis.py` (`analyze`) computing critical
  path, total work, max theoretical speedup (work/span), top-5 critical-path
  ops, explicit host/device transfer boundaries, coarse CPU/GPU device
  residency timeline, and candidate fork/join parallel regions. Added
  `experimental/tracer/src/tracer/reports.py` and `tracer/run.py` to generate
  Markdown + Graphviz DOT reports per workload from a single CLI invocation,
  and `experimental/tracer/tests/test_analysis.py` with 8 unit tests.
  Generated `experimental/tracer/reports/{parquet_feature_inference,
  model_ensemble,cv_preprocess_inference_postprocess}.{md,dot}` and the
  findings memo `docs/benchmarks/phase0-tracer-findings.md`. Key observations:
  parquet feature-to-GPU transfer dominates its critical path (~50 %);
  model_ensemble has a named fork/join parallel region between the two
  independent branches (~12–17 % span-reduction opportunity); CV shows a clean
  CPU-preprocess → GPU-inference → CPU-postprocess phase boundary and ~44 ms
  of per-weight host→device transfers inside resnet18. Updated tracer README
  with analysis/CLI usage. Adjusted the sprint Validation block to use
  `--workload all` so the report-count check is internally consistent.
  Validation commands pass: 34 tracer tests, 3 reports, findings memo exists,
  `./scripts/check.sh` passes. Sprint now `needs_validation`; next prompt is
  P1 (Validator).

- [2026-08-11][executor PR #45 follow-up] Resolved the PR review and failing CI
  findings. Added regression tests and fixes for exact integer leaves, baseline
  reuse during verification, per-workload correctness tolerances, deterministic
  fixed warmup, cuDF subprocess isolation, nested handles, read-before-write
  ordering, earliest common joins, exclusive branch-work accounting, pandas
  and torch-to-NumPy boundaries, and CUDA completion timing. Formatted the
  committed correctness artifact, regenerated tracer reports and the findings
  memo, and removed unsupported empty-C++/CodeQL upload paths from CI.
  Validation passes: `./scripts/check.sh --ci`, 41 tracer tests, and 17
  pipeline tests. Sprint remains `needs_validation`; next prompt is P1.

- [2026-08-11][executor PR #45 review follow-up 2] Added regression tests and
  fixes for the second review batch: one persistent cuDF-isolated worker with
  cached compiled models, pandas `__setitem__`/Series arithmetic/`get_dummies`/
  `concat` boundaries, generation-aware tensor allocation handles, propagated
  `equal_nan` and tolerance-map merging, and memoized reachability in parallel
  region analysis. Made CodeQL language detection source-backed so C++/CUDA is
  included automatically when native sources land; upload remains disabled
  only because the private repository's Advanced Security setting is off and
  requires owner approval. Regenerated tracer reports/findings from the new
  recorder behavior. Validation passes: `./scripts/check.sh --ci`, 44 tracer
  tests, 5 parquet tests, and local actionlint. Awaiting the CodeQL setting and
  Devin approval.

- [2026-08-11][executor PR #45 review follow-up 3] Closed the next review batch:
  CI now runs the pipelines/tracer packages with GPU-only cases marked and
  runs strict mypy for `cobra_pipelines`; CUDA-only dependencies are Linux
  gated in the package and lockfile. Preserved root ndarray lineage across the
  pandas/NumPy boundary, recorded mutation metadata so read-only views do not
  become producers, and fenced opaque calls against all live frontiers. The
  persistent parquet worker now uses an explicit environment allowlist and
  `stderr=DEVNULL`, preventing diagnostic-pipe deadlocks and credential
  propagation. Regenerated the doctor artifact, 180 raw timing samples,
  statistical analysis, parquet Nsight traces/summaries, tracer reports, and
  findings memo. Validation passes: `./scripts/check.sh --ci`, 48 tracer
  tests, 187 package tests with 9 GPU tests deselected, and `git diff --check`.
  CodeQL upload remains owner-controlled because Advanced Security is disabled;
  awaiting that setting and Devin approval.

- [2026-08-11][executor PR #45 CI follow-up 4] Diagnosed the remote config-lint
  failure from run `31546559559`: `raven-actions/actionlint@v2.2.0` invokes
  pipx, whose current backend rejects the workflow's `uv 0.7.14` because it
  requires `uv >=0.9.17`. Updated `.github/workflows/ci.yml` to `uv 0.9.17`;
  local config/docs/shell lint and `git diff --check` pass. The fix is ready to
  push; CodeQL upload remains the only review thread intentionally open.

- [2026-08-11][executor PR #45 review follow-up 5] Added failing-first tests
  and fixes for the new Devin findings: pandas comparison/boolean/notna/
  reset-index boundaries and DataFrame construction writes; NumPy
  `__array_ufunc__` subtraction/division lineage; the patched `torch.from_numpy`
  boundary; descriptor-safe mutation detection in the Torch adapter and DAG;
  and a JSON per-run configuration protocol for the persistent parquet worker.
  Updated the raw evidence manifest to the measured `c9c1a89` revision and
  regenerated the three tracer reports plus findings memo. `./scripts/check.sh
  --ci` passes with 193 tests and 9 GPU tests deselected. Next: commit/push and
  monitor CI and Devin; Advanced Security remains owner-controlled.

- [2026-08-11][executor PR #45 review follow-up 6] Added failing-first tests
  and fixes for logical view lineage, generation-aware pandas/NumPy handles,
  exact integral-vs-float correctness, and empty tracer analysis. Updated the
  tracer README, regenerated reports/findings, and verified that view consumers
  retain producer lineage. `./scripts/check.sh --ci` passes with 196 tests and
  9 GPU tests deselected. Next: commit/push and monitor CI/Devin; CodeQL and
  release/publish security gate findings remain owner-controlled.

- [2026-08-11][executor PR #45 review follow-up 7] Added failing-first tests
  and fixes for cuDF distribution discovery across CUDA/package variants and
  generation-safe opaque handles. Non-weakrefable container identities are
  omitted rather than reused after collection, while nested trackable values
  remain recursive. Updated the tracer README and regenerated reports to
  confirm the graph is unchanged; timing-only report churn was retained out
  of the validated evidence set. `./scripts/check.sh --ci` passes with 199
  tests and 9 GPU tests deselected. Next: commit/push and monitor CI/Devin;
  CodeQL and release/publish gate findings remain owner-controlled.

- [2026-08-11][executor PR #45 review follow-up 8] Added failing-first tests
  and fixes for exclusive nested recorder durations, suppression/filtering of
  recorder-internal Torch metadata reads, explicit CV synthetic-generation and
  postprocessing boundaries, cached compiled MLP/Transformer/ResNet models,
  and persistent-worker stderr diagnostics via a non-blocking temporary file.
  Regenerated the three tracer reports and findings memo: 88 parquet, 346
  model, and 1,899 CV events. `./scripts/check.sh --ci` passes with 205 tests
  and 9 GPU tests deselected. Next: commit/push and monitor CI/Devin; CodeQL
  upload and release/publish gate findings remain owner-controlled.

- [2026-08-11][executor PR #45 review follow-up 9] Diagnosed the CI-only
  failure of `test_tracer_overhead_under_10x_eager`: the Torch hot path queried
  CUDA availability for every CPU event and repeated tensor storage identity
  inspection within one event. Added a failing-first regression test, cached
  availability per `TraceSession`, short-circuited CUDA checks for CPU values,
  reused storage identities and object visits within each event, and kept
  argument summaries free of allocation-identity work. Targeted tracer tests,
  repeated overhead runs, and `./scripts/check.sh --ci` pass with 206 tests and
  9 GPU tests deselected. Next: commit/push and monitor CI/Devin; CodeQL upload
  and release/publish gate findings remain owner-controlled.

- [2026-08-11][executor PR #45 review follow-up 10] Added failing-first fixes
  for the four new functional findings: `_float_key` now inspects both
  expected and actual scalar types before defaulting; `cobra-bench run` writes
  the measured Git revision and doctor-collected host/CUDA/software metadata
  instead of copying the placeholder suite template; B0 now caches eager MLP,
  Transformer, and ResNet models alongside the existing B1 compiled caches so
  warm timing scopes are symmetric. Targeted harness and pipeline tests pass.
  Next: regenerate phase-0 timing/analysis evidence from this clean revision,
  update the baseline report, then monitor CI/Devin; CodeQL upload and
  release/publish gate findings remain owner-controlled.
