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
- [ ] Do: from recorded wall times: critical-path length, total work,
  max theoretical speedup (work/span), device residency timeline
  (which values bounce host↔device and when), transfer count estimate.
  Emit `experimental/tracer/reports/<workload>.md` + rendered DAG.
- Accept: three workload reports exist with: span/work ratio, top-5
  critical-path ops, observed transfer boundaries, and candidate
  parallel regions (named).

### T4 — Findings memo
- [ ] Do: `docs/benchmarks/phase0-tracer-findings.md` — for each
  workload: the 2-3 concrete optimization opportunities visible in the
  DAG (e.g., "branches A/B independent: 41% span reduction if
  overlapped"; "df→tensor crosses host needlessly"). Explicitly mark
  which opportunities a tensor-only compiler (torch.compile alone)
  CANNOT see — this feeds the S05 gate criterion.
- Accept: memo lists ≥2 cross-library opportunities total, each with a
  quantified estimate from trace data.

## Validation

```bash
uv run pytest experimental/tracer -q
uv run python -m tracer.run --workload parquet_feature_inference \
  --out experimental/tracer/reports/
ls experimental/tracer/reports/*.md | wc -l   # == 3
test -f docs/benchmarks/phase0-tracer-findings.md
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; three reports + findings memo committed
- [ ] `experimental/tracer/README.md` opens with "DISPOSABLE — not
      release code" (plan §18.4)
- [ ] STATE.md + Session log updated; committed on sprint branch

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
