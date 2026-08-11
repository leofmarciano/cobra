# S25 — Fuzzing, sanitizers, failure injection

| Field | Value |
|---|---|
| Milestone | M4 — v0.1 hardening & release |
| Depends on | S24 (done) |
| Hardware | **NVIDIA GPU required** (compute-sanitizer lanes) |
| Estimated sessions | 2-3 |
| Plan sections | §19.8, §19.13-19.14, §34.2-34.4, §34.7, §24.2 (fuzz/sanitizer gates) |

## Objective

Build the adversarial qualification machinery: the full §19.8 fuzz
target set with corpus management and cumulative-execution tracking
(gate: ≥10M executions, no unresolved reproducible crash), complete
sanitizer CI lanes, and the §19.14 failure-injection framework.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §19.8 (targets), §19.13 (sanitizer list),
   §19.14 (injection list), §34.2-34.4/§34.7 (lane commands), §24.2
   fuzz/sanitizer/soak gate lines
3. Fuzz infra from S10 (`scripts/fuzz.sh`, existing targets, triage
   doc)

## Out of scope

- Remote-cache fuzzing (no remote cache in v0.1). Plugin ABI fuzzing
  (no stable ABI until v1). The 24h soak itself (S28 runs it; this
  sprint builds the harness pieces it needs).

## Tasks

### T1 — Complete the native fuzz target set
- [ ] Do: add to S10's two: `cobra_guard_fuzzer` (guard evaluator over
  serialized guard forms), `cobra_scheduler_fuzzer` (event-sequence /
  dependency-graph construction per §19.8), `cobra_cache_meta_fuzzer`
  (cache meta.json + quarantine paths). Structured-input helpers
  (protobuf-style or custom mutators) where raw bytes are too weak.
- Accept: all five targets build in `fuzz` preset; each runs 10 min
  locally clean; seed corpora committed.

### T2 — Python structured fuzzing
- [ ] Do: generator producing random supported-op capture programs
  (tensor+dataframe call mixes, graph-break placements, exception
  paths, mutation patterns per §19.8 python-side list) executed in
  differential mode; deterministic replay from seed (§19.8: "must
  support deterministic replay from a seed").
- Accept: 10k-program run green on GPU host (or divergences → S24
  regressions + fixes/flags); seed replay reproduces byte-identical
  programs.

### T3 — Cumulative-execution ledger
- [ ] Do: fuzz runs append (target, commit, seconds, execs, crashes) to
  `artifacts/qualification/fuzz-ledger.jsonl` (merged, not overwritten;
  the S28 gate sums it). `scripts/fuzz-campaign.sh` runs all targets
  for N hours and updates the ledger; document how overnight runs on
  the GPU host accumulate toward 10M.
- Accept: ledger math verified by test; one real multi-hour campaign
  recorded (kick off overnight, record actuals).

### T4 — Sanitizer lanes complete
- [ ] Do: finalize CI lanes per §34.2-34.4: asan-ubsan full unit+lit
  lane, tsan runtime lane, GPU lane running compute-sanitizer
  memcheck/racecheck/synccheck/initcheck over release-critical CUDA
  test sets (document which runners; manual-run fallback per PROTOCOL
  if no GPU CI runner — results pasted into Session log + artifact
  file). LeakSanitizer where compatible (§19.13).
- Accept: all lanes green at this commit; lane docs in
  `docs/process/ci-lanes.md`.

### T5 — Failure-injection framework
- [ ] Do: unify S14-T4 into a general deterministic injection framework
  covering the §19.14 v0.1 list: host/CUDA alloc failure, launch/sync
  failure, corrupt cache entry, incompatible artifact stub, disk full,
  cancellation mid-pipeline, dataframe fallback failure; every
  injection: resources released, useful error, no partial output
  (§19.14 contract).
- Accept: each point has a test; leak counters at baseline after every
  injection; docs list injection env-vars/flags.

## Validation

```bash
cmake --preset fuzz && cmake --build --preset fuzz
for t in ir_text ir_bytecode guard scheduler cache_meta; do \
  ./scripts/fuzz.sh cobra_${t}_fuzzer 120; done
uv run pytest test/python/test_structured_fuzz.py -q --seed 42
ctest --preset asan-ubsan && ctest --preset tsan
uv run python scripts/fuzz-ledger-report.py   # prints cumulative execs
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; five native targets + python fuzzer + ledger
      operational; sanitizer lanes documented and green
- [ ] Injection framework covers the §19.14 v0.1 list
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S28 sums the ledger (needs ≥10M — schedule overnight campaigns from now
on, every GPU-host idle night counts) and runs the sanitizer matrix as
gate evidence. S26/S27 proceed in parallel work-order (still WIP=1).

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
