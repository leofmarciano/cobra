# S09 — Python extension & first capture

| Field | Value |
|---|---|
| Milestone | M1 — Compiler skeleton |
| Depends on | S07, S08 (done) |
| Hardware | CPU-only |
| Estimated sessions | 2-3 |
| Plan sections | §6.1, §15.1, §15.3, §35 Epic 2, §23 Phase 1 exit |

## Objective

Connect Python to the native core: a `_native` extension exposing IR
building + runtime execution, and the first real `@cobra.compile`
capture path. Exit = the plan's Phase 1 criterion: *"a pure two-node DAG
can be captured, serialized, loaded, scheduled, and explained."*

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §6.1 (capture flow 1-8), §15.1 (language
   table), §35 Epic 2 acceptance
3. Headers from S07 (dialect API) and S08 (`include/cobra/runtime/`)

## Out of scope

- Real adapters (torch/pandas — S16/S17). Guards (S11). Graph breaks
  beyond a hard error on unknown calls (S12 makes them safe). Cache.
  Wheels (S27).

## Tasks

### T1 — Binding layer decision + skeleton (ADR-0007)
- [ ] Do: choose nanobind vs pybind11 (evaluate: MLIR CAPI friendliness,
  build simplicity under scikit-build-core, maintenance); record
  ADR-0007. Build `python/cobra_compiler/_native/` module via CMake;
  make `uv run pytest` able to import it (editable build documented in
  `docs/guides/building.md`).
- Accept: `import cobra_compiler._native` works in-container; version
  string round-trips from C++.

### T2 — IR construction API (thin)
- [ ] Do: expose over the C++ dialect API: create module, add
  `cobra.program.call` nodes with effect attrs + source locations, add
  fork/join, verify, print to text, save/load bytecode. Python-side
  wrapper `cobra_compiler/capture/graph.py` with typed methods.
- Accept: pytest builds the §7.4-shaped two-branch graph from Python,
  verifies it, round-trips bytecode, and FileCheck-matches the printed
  IR (test stored under `test/python/`).

### T3 — Capture context + decorator v0
- [ ] Do: `@cobra.compile` + `cobra.capture()` context manager
  implementing §6.1 steps 1-6 for a WHITELISTED callable registry
  (explicitly registered pure Python functions only, via
  `cobra.task(...)` marker for now): wrap inputs in proxies, record
  calls as graph nodes, defer execution, materialize on exit. Unknown
  calls raise `CobraUnsupportedError` (safe graph breaks come in S12 —
  document this loudly).
- Accept: differential test — decorated pipeline of 2 registered
  functions returns bit-identical results to undecorated execution.

### T4 — Execute through the native runtime
- [ ] Do: lower the captured graph to S08 `TaskGraph` (each call node =
  one task holding the Python callable; fork/join = deps); execute via
  the native executor with the GIL released around native waits
  (callables re-acquire); propagate exceptions per §8.3 (source-order).
- Accept: two independent nodes execute on two pool threads (assert via
  thread ids in a test callable); exception from node 1 surfaces even
  when node 2 also fails (1000-run determinism test).

### T5 — Fingerprinting + explain v0 groundwork
- [ ] Do: callable fingerprint = hash(code object bytes + closure
  const repr + `cobra_compiler` version) in
  `capture/fingerprint.py`; `cobra.explain(fn, sample_inputs)` returns a
  dict: captured node count, node list with source spans, parallel
  fork/join structure (renders via S10's formatter later).
- Accept: fingerprint changes when function body changes, stable across
  process restarts; explain dict snapshot-tested.

## Validation

```bash
cmake --build --preset dev --target cobra-native-ext
uv run pytest test/python -q
# Phase-1 exit demo (also a pytest):
uv run python examples/two_node_dag.py   # captures, saves, loads, runs, explains
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; Phase-1 exit demo committed as example + test
- [ ] ASan build of the extension passes pytest (document invocation)
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S10 lowers S03 tracer JSON through the T2 API and formats explain
output. S11 attaches guards to T5 fingerprints. Keep proxy internals
private — adapters must go through `capture/graph.py`.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
