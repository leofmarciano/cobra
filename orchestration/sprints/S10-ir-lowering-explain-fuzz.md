# S10 — Tracer-JSON→IR lowering, explain v0, parser fuzzing

| Field | Value |
|---|---|
| Milestone | M1 — Compiler skeleton |
| Depends on | S09 (done) |
| Hardware | CPU-only |
| Estimated sessions | 2 |
| Plan sections | §29 (Days 31-45 end), §3.4, §19.8, §22.1 |

## Objective

Close the Phase-0→Phase-1 bridge: convert S03 tracer output into real
Cobra IR (proving the IR can represent the three workloads), ship the
first human-readable `cobra explain` formatter, and stand up fuzzing for
everything that parses untrusted bytes.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §3.4 (explain output shape), §19.8 (fuzz
   target list), §29 Days 31-45 ("lower the disposable trace into Cobra
   IR")
3. `experimental/tracer/README.md` (JSON schema, S03)
4. `python/cobra_compiler/capture/graph.py` API (S09)

## Out of scope

- Optimizations/passes. Executing the lowered workload IR end-to-end
  (adapters don't exist yet — lowering is structural). Artifact
  container format (S27 area; only IR/bytecode fuzzing here).

## Tasks

### T1 — Tracer JSON → Cobra IR converter
- [ ] Do: `python/cobra_compiler/capture/from_trace.py`: map tracer
  events to `cobra.program.call` nodes (opaque targets), value lineage
  to SSA, conservative effect attrs (unknown → full barrier), source
  locations preserved; independent branches become fork/join.
- Accept: all three S02 workload traces lower to VERIFIED modules;
  `model_ensemble` IR contains a fork/join pair (FileCheck test on
  printed IR).

### T2 — `cobra explain` formatter v0
- [ ] Do: `python/cobra_compiler/diagnostics/explain.py`: text + JSON
  renderer for a module: captured nodes, fallback/opaque nodes,
  parallel regions, per-node source span + effects (subset of the §3.4
  block relevant pre-placement). CLI stub `cobra explain <module.py:fn>`
  wired via a console script entry point.
- Accept: snapshot tests (text + JSON) for the three lowered workloads;
  JSON schema documented in `docs/reference/explain-schema.md`.

### T3 — Fuzz infrastructure + first targets
- [ ] Do: activate the `fuzz` CMake preset (libFuzzer): targets
  `cobra_ir_text_fuzzer` (parser) and `cobra_ir_bytecode_fuzzer`
  (reader) per §19.8; seed corpora from existing test files;
  `scripts/fuzz.sh <target> <seconds>`; crash artifacts auto-saved to
  `test/Fuzz/corpus/…` and a triage doc `docs/process/fuzz-triage.md`.
- Accept: both fuzzers build and run 10 minutes locally with zero
  crashes (fix anything found first); corpus committed.

### T4 — CI short-fuzz lane
- [ ] Do: extend native CI: 60-second run of each fuzzer per PR
  (regression corpus replay + short exploration), failing on any crash;
  nightly-length runs documented for later (S25 wires them fully).
- Accept: lane green; a deliberately-broken parser branch (local test)
  is caught by corpus replay.

## Validation

```bash
uv run pytest test/python -q
uv run python -m cobra_compiler.capture.from_trace \
  experimental/tracer/reports/model_ensemble.json | \
  ./build/dev/bin/cobra-opt --verify-diagnostics
cmake --preset fuzz && cmake --build --preset fuzz
./scripts/fuzz.sh cobra_ir_text_fuzzer 60
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; three workloads visible in cobra-opt (§29
      Days 31-45 output)
- [ ] Fuzzers running in CI; triage doc exists
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S11 adds guards/caching around captured modules; S12's explain additions
(graph-break reasons) extend the T2 formatter. The T1 converter is
throwaway-adjacent (the tracer is disposable) but its IR patterns are the
reference for S16/S17 adapters.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
