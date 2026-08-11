# S12 — Graph breaks, fallback contract, shadow mode

| Field | Value |
|---|---|
| GitHub issue | #13 |
| Milestone | M1 — Compiler skeleton (closes it) |
| Depends on | S11 (done) |
| Hardware | CPU-only (GPU optional for corpus variety) |
| Estimated sessions | 2-3 |
| Plan sections | §6.3, §6.5, §3.3, §18.5, §29 (Days 46-60), §23 Phase 2 exit |

## Objective

Make "unsupported" SAFE: graph breaks with stable reason codes, a
fallback path that provably preserves observable Python behavior, shadow
mode that catches wrong-code in production style, and the first
15-program differential corpus. Exit = plan Phase 2 criteria (scaled to
15 programs; the corpus grows to 25→50 in S24).

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §6.3 (break triggers + required fields),
   §6.5 (fallback contract + overhead budget), §3.3 (shadow mode row),
   §18.5 (wrong-code policy)
3. `docs/decisions/ADR-0005-semantic-charter.md`
4. `capture/` APIs from S09/S11; explain formatter from S10

## Out of scope

- Framework adapters (S16/S17) — corpus uses plain Python + registered
  functions + numpy-lite cases. Optimizations. The 5% overhead GATE
  measurement (measured here, ENFORCED at S28).

## Tasks

### T1 — Graph-break reason registry
- [ ] Do: `python/cobra_compiler/diagnostics/reasons.py`: stable IDs
  (e.g., `GB-UNKNOWN-CALLABLE`, `GB-MUTATION-UNMODELED`,
  `GB-DYNAMIC-BRANCH`, `GB-UNSUPPORTED-TYPE`, `GB-GUARD-BUDGET`,
  `GB-UNPROFITABLE`…), each with: message template, source-location
  capture, remediation hint, and docs page anchor (§6.3 required
  fields). Explain output (S10) renders them.
- Accept: registry is append-only (test asserts IDs never renumber);
  every break site in the codebase uses a registered ID (grep-test).

### T2 — Safe graph break + fallback execution
- [ ] Do: replace S09's `CobraUnsupportedError` with real behavior:
  unknown call → materialize minimal required subgraph → execute the
  unknown eagerly → resume capture after (§6.1 steps 6-7). Enforce the
  §6.5 "never silently" list: exceptions propagate unchanged (type +
  message + traceback chain), warnings re-emitted, stdout/stderr order
  preserved around ordered-effect nodes, mutations happen exactly once.
- Accept: contract tests for each §6.5 bullet (exception, warning,
  stdout order, no-skip, no-reorder, mutation-once).

### T3 — Shadow mode
- [ ] Do: `mode="shadow"`: run reference eager AND captured path on the
  same inputs (RNG state captured/restored around both, §8.4), compare
  outputs (exact for ints/str/bool; per-dtype tolerance hooks for
  floats), return the REFERENCE result, log divergence with source
  span + values summary (§3.3).
- Accept: fault-injection test — a deliberately wrong captured node is
  detected and reported by shadow mode (Phase 2 exit criterion); RNG
  restoration verified.

### T4 — Differential corpus v1 (15 programs)
- [ ] Do: `test/Differential/corpus/` — 15 curated programs covering:
  pure orchestration, fan-out/fan-in, mutation-forces-break, exception
  paths, warnings, stdout ordering, RNG use, closure constants, kwargs/
  defaults, generator-materialization, dict/list aliasing, unsupported
  C-extension call, guard-miss recompile, storm→fallback, nested
  capture. Each runs: eager vs captured vs shadow; a pytest lane runs
  all three (§34.6 shape).
- Accept: 15/15 pass all modes; each program documents WHAT semantic
  rule it defends (docstring).

### T5 — Fallback overhead measurement + wrong-code workflow
- [ ] Do: pyperf bench of a fully-unsupported function decorated vs
  undecorated (warm) — record p50 overhead in the Session log +
  `docs/benchmarks/fallback-overhead.md` (v0.1 gate: ≤5%, §6.5 — fix
  the obvious if over, else record as known gap for S28). Write
  `docs/process/wrong-code.md`: report → disable-by-default → minimized
  regression → fix → advisory decision (§18.5).
- Accept: overhead number recorded with methodology; process doc
  complete.

## Validation

```bash
uv run pytest test/Differential -q
uv run pytest test/python/test_fallback_contract.py test/python/test_shadow.py -q
uv run python benchmarks/micro/bench_fallback_overhead.py
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; Phase 2 exit criteria demonstrated (corpus
      green, guards trigger recompile/fallback correctly, unsupported
      mutation + I/O break safely, shadow catches injected fault)
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

M1 is complete. S13 starts the scheduler policy layer (pure native, no
Python). S16/S17 will route THEIR unsupported ops through T1/T2
machinery — reason IDs are already reserved for adapter breaks.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
