# S18 — DLPack handoff & memory ownership

| Field | Value |
|---|---|
| Milestone | M3 — Integration & evidence |
| Depends on | S16, S17 (done) |
| Hardware | **NVIDIA GPU required** |
| Estimated sessions | 2-3 |
| Plan sections | §11.1-11.4, §35 Epic 7, §28 (zero-copy lifetime risk row) |

## Objective

Formalize value ownership so zero-copy stops being scary: every runtime
value carries the §11.3 descriptor; DLPack/Arrow handoffs follow
explicit producer/consumer lifetime contracts with stream-correct
synchronization; copies are accounted, not accidental. The plan flags
zero-copy lifetime bugs as a critical risk — this sprint is the
mitigation.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §11.1 (DLPack tracking list), §11.2
   (columnar), §11.3 (descriptor fields), §11.4 (planner features —
   implement lifetime/reuse subset), §35 Epic 7 acceptance
3. Boundary code from S16 T4 and S17 T4 (the conservative syncs to
   replace)

## Out of scope

- Full memory PLANNER with lifetime-overlap buffer reuse optimization
  (v0.1 needs the tracking + pools; global reuse planning matures in
  S19/S23). Spill-to-host (§11.5 step 4 — post-v0.1). Buffer donation.

## Tasks

### T1 — Value descriptor + lifetime tokens
- [ ] Do: `runtime/core/value.h`: descriptor with §11.3 fields (logical
  /physical type, shape/schema ref, device+memory space, storage
  identity, owner, borrow count/lifetime token, mutation permission,
  last-writer event, expected release point); Python-side handle keeps
  native descriptor alive; debug mode logs create/borrow/release with
  storage ids.
- Accept: unit tests: borrow prevents release; release with live
  borrows is an error (not a crash); descriptor survives adapter
  round-trips.

### T2 — DLPack contracts (torch boundary)
- [ ] Do: import/export via DLPack managed tensors honoring §11.1:
  deleter wired to lifetime token, producer-stream → consumer-stream
  sync via events (record last-writer event; consumer waits BEFORE
  first use, no device-wide sync), read-only flag enforced (mutation of
  borrowed-read-only → error), dtype/shape/stride fidelity tests.
- Accept: replace S16-T4 conservative syncs; ensemble example still
  oracle-clean over 1000 runs; an intentionally-missing sync test
  (debug hook) is CAUGHT by the last-writer-event assertion.

### T3 — Arrow C Data/Device contracts (dataframe boundary)
- [ ] Do: same treatment for S17-T4: Arrow C Data (host) and C Device
  (GPU) structs with release-callback wired to lifetime tokens; cuDF→
  torch path documents exactly which cases are zero-copy vs single-pack
  (nulls, non-contiguous columns → pack); decision logged per
  conversion node.
- Accept: pointer-identity test for the zero-copy case; pack cases
  produce exactly-one copy (counter assert).

### T4 — Copy accounting + explain integration
- [ ] Do: global per-execution counters (h2d bytes, d2h bytes, d2d
  bytes, pack copies, materializations) attributed to graph nodes;
  explain renders the §3.4 "expected host-to-device copies / copies
  removed" block from real counters; cobra-bench result schema fields
  (`h2d_bytes`, `d2h_bytes`) now filled from these counters.
- Accept: `parquet_feature_inference` explain shows the GPU-resident
  route eliminating N bytes vs CPU route (numbers from counters, test
  asserts nonzero elimination).

### T5 — Fault suite
- [ ] Do: Epic 7 acceptance tests: producer freed before consumer
  (must be prevented by token), double-release, early stream reuse,
  cross-stream read-before-write; run under compute-sanitizer
  (memcheck + racecheck) and ASan for host paths.
- Accept: all fault tests pass; sanitizers clean; each §28 zero-copy
  risk bullet maps to at least one test (traceability table in test
  README).

## Validation

```bash
uv run pytest test/python/interop -q                  # GPU host
ctest --preset dev -R ownership
compute-sanitizer --tool memcheck ./build/dev/bin/cobra-interop-tests
compute-sanitizer --tool racecheck ./build/dev/bin/cobra-interop-tests
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted (Epic 7: low/zero-copy per contract, producer
      outlives consumers, cross-stream green, fault suite green)
- [ ] Ownership rules documented in `docs/architecture/ownership.md`
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S19's transfer-elimination pass relies on T4 counters as its oracle
("copies removed" must be measured, not assumed). The descriptor is now
the only legal way values cross adapter boundaries.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
