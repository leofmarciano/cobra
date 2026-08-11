# S22 — Effect & alias analysis hardening

| Field | Value |
|---|---|
| GitHub issue | #23 |
| Milestone | M4 — v0.1 hardening & release |
| Depends on | S21 = go |
| Hardware | **NVIDIA GPU required** (adapter alias tests) |
| Estimated sessions | 3 |
| Plan sections | §8.1-8.4, §19.11, §35 Epic 4 |

## Objective

Replace the conservative-everywhere effect handling that got us through
M3 with the real analysis the optimizer needs: full effect taxonomy in
IR, library-specific alias models, ordered barriers, the finalized
exception commit model, and RNG policy — all proven by the §19.11 test
list. Precision here is what unlocks S23's optimizer without wrong-code.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §8.1 (lattice), §8.2 (alias models per
   library), §8.3 (exceptions), §8.4 (RNG), §19.11 (required cases)
3. `docs/decisions/ADR-0005-semantic-charter.md` (the contract)
4. Adapter alias hooks from S16-T3, S17 schema metadata

## Out of scope

- Interprocedural Python analysis (adapters + annotations only).
  `@cobra.pure`/`@cobra.effects` TRUST modes (§3.1 — declare API,
  validate in debug/shadow, but "trust mode" UB semantics stay
  post-v0.1). Window/extension-array dataframe aliasing (fallback).

## Tasks

### T1 — Effect taxonomy end-to-end
- [ ] Do: complete `#cobra.effect` usage: adapters emit precise effects
  (torch: read/write on storage alias sets, device_state for stream
  ops; dataframe: read/write on frame lineage; io nodes: fs/net/stdout
  classes; RNG: `random(state_id)`); effect-join rules implemented as
  dialect utilities with unit tests (conflict matrix from §8.1
  parallelism conditions).
- Accept: conflict-matrix table test (every effect pair → may-overlap
  verdict) matches the charter exactly.

### T2 — Alias analysis per library
- [ ] Do: `lib/Analysis/AliasAnalysis/`: tensor rule set (storage
  identity, views share base alias set, strides/offsets tracked,
  version-counter observation, in-place = write to storage set);
  dataframe rules (logical plans vs materialized objects, `inplace=`
  and view-like ops conservative, unknown extension → unknown alias);
  Python objects default-unknown with precision for immutables/frozen
  dataclasses (§8.2 all three lists).
- Accept: view-aliases-base test; slice-of-slice; df view mutation
  serializes; immutable args allow overlap — each as lit/pytest.

### T3 — Ordered barriers + annotations API
- [ ] Do: filesystem/network/stdout/global/RNG barriers enforced in
  scheduling legality (unknown = full barrier stays); implement
  `@cobra.pure`, `@cobra.effects(reads=,writes=)`, `@cobra.task`
  declaration APIs (§3.1) — validated in debug/shadow mode (a false
  purity declaration is DETECTED in shadow: §3.1 "user annotations are
  assertions").
- Accept: false-`@cobra.pure` test → shadow flags divergence + warning
  with source span; annotated-true case unlocks overlap (sim assert).

### T4 — Exception commit + RNG policy finalization
- [ ] Do: finalize §8.3 (source-order winner, suppressed diagnostics in
  debug, no reorder across throwing effectful ops, cancellation
  best-effort, OOM reported with schedule context) in the REAL runtime
  (S13 did sim; wire identical semantics through S14 paths). RNG: §8.4
  strict default (shared stateful generator serializes; framework RNG
  state capture/restore in shadow — extends S12-T3), `reproducible`
  and `off` modes flagged.
- Accept: GPU exception-race test (1000 runs, deterministic winner);
  RNG serialization test; shadow RNG restore test.

### T5 — §19.11 suite complete
- [ ] Do: implement every §19.11 bullet as a named test (independent-
  pure-parallel, read/read overlap, read/write serialize, write/write
  serialize, view-alias, uncertain-alias serialize in safe mode,
  file-I/O ordered, logging ordered, global mutation ordered, RNG per
  mode, exception contract, cancellation no-partial-state).
- Accept: suite green under dev + tsan presets; each test cites its
  bullet in a docstring (traceability).

## Validation

```bash
cmake --build --preset dev --target check-cobra-unit check-cobra-lit
uv run pytest test/python/test_effects.py test/python/test_aliases.py \
  test/python/test_annotations.py -q
ctest --preset tsan -R effects
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; §19.11 fully covered (Epic 4 acceptance)
- [ ] Charter cross-reference table committed
      (`docs/architecture/effects.md`: charter rule → test name)
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S23's optimizer legality queries T1/T2 exclusively — no pass may invent
its own aliasing judgment. The annotations API is now public surface
(S26 documents it).

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
