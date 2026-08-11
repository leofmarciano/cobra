# S07 — MLIR dialect skeleton (CobraProgram + CobraEffect)

| Field | Value |
|---|---|
| Milestone | M1 — Compiler skeleton |
| Depends on | S06 (done) |
| Hardware | CPU-only |
| Estimated sessions | 3-4 |
| Plan sections | §7.1-7.5, §8.1, §35 Epic 1, §34.5 |

## Objective

Implement the minimum viable Cobra dialects: `cobra.program` operations
with effect tokens, verifiers, parser/printer round-trips, and the
`cobra-opt` tool with lit/FileCheck test infrastructure. This is the IR
every later sprint targets.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §7.1 (principles), §7.2 (`cobra.program`
   op list), §7.4 (effect SSA example), §7.5 (invariants), §8.1 (effect
   lattice), §34.5 (lit lane)
3. `docs/decisions/ADR-0005-semantic-charter.md` (frozen at S05)
4. MLIR upstream docs as needed (ODS/TableGen) — fetch selectively

## Out of scope

- `cobra.tensor`, `cobra.rel`, `cobra.schedule` dialects (they arrive
  with their adapters/planner in S16/S17/S19 as needed). Lowerings.
  Bytecode versioning beyond a format-version attribute. Passes.

## Tasks

### T1 — Dialect scaffolding
- [ ] Do: `lib/Dialect/CobraProgram/` + `include/cobra/…` per repo
  layout: dialect registration, ODS TableGen for ops `region, call,
  fallback, guard, materialize, fork, join, raise, cancel`; a
  `!cobra.token` type for effect ordering (§7.4); `#cobra.effect<…>`
  attribute encoding the §8.1 lattice (pure/read/write/mutate/global/
  fs/net/stdout/warning/random/device/sync/unknown + alias-set payload).
  Source provenance: every op carries a location (MLIR built-in) and
  the dialect verifier rejects unknown-loc in strict mode.
- Accept: `cobra-opt` (T3) parses+prints every op; ops have ODS
  descriptions (they become docs).

### T2 — Verifiers + invariants
- [ ] Do: implement §7.5-relevant verifiers now: token operands are
  single-use-ordered (conflicting effects must be chained), fork/join
  arity consistency, guard ops reference declared guard kinds, region
  isolation rules. Diagnostics must carry source locations and be
  actionable.
- Accept: every verifier has a negative test (malformed IR → located
  diagnostic, checked by FileCheck).

### T3 — `cobra-opt` + lit infrastructure
- [ ] Do: `tools/cobra-opt/` (MlirOptMain with Cobra dialects
  registered); wire `llvm-lit` + FileCheck into CMake
  (`check-cobra-lit` target); `test/Dialect/CobraProgram/*.mlir` with
  round-trip tests including the §7.4 example program rewritten in real
  syntax.
- Accept: `cmake --build --preset dev --target check-cobra-lit` green;
  §7.4-style program round-trips text→parse→print→reparse identically.

### T4 — Bytecode round-trip + format version
- [ ] Do: enable MLIR bytecode read/write for the dialect; embed a
  `cobra.ir_version` module attribute; test text↔bytecode↔text
  equality; reading a bumped-major version fails closed with a clear
  error (cache-safety groundwork, §17.6).
- Accept: lit tests cover round-trip + version-mismatch rejection.

### T5 — Doc generation
- [ ] Do: hook `mlir-tblgen -gen-dialect-doc` into the build; emit
  `docs/reference/dialects/cobra_program.md`; CI fails when docs are
  stale (regen + diff check in `scripts/check.sh` native section).
- Accept: generated doc committed and current.

## Validation

```bash
cmake --build --preset dev --target cobra-opt check-cobra-lit
./build/dev/bin/cobra-opt test/Dialect/CobraProgram/roundtrip.mlir
cmake --preset asan-ubsan && cmake --build --preset asan-ubsan --target check-cobra-lit
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; lit suite green in dev AND asan-ubsan presets
- [ ] Every op family has ≥1 positive and ≥1 negative test (Epic 1
      acceptance)
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S09 binds these dialects through the Python extension; S10 lowers tracer
JSON into this IR. Keep op syntax stable — changes after S09 require a
Session-log note and test updates in dependents.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
