# S11 — Guards & specialization cache

| Field | Value |
|---|---|
| Milestone | M1 — Compiler skeleton |
| Depends on | S09 (done) |
| Hardware | CPU-only |
| Estimated sessions | 2-3 |
| Plan sections | §6.4, §17.6, §35 Epic 3, §29 (Days 46-60) |

## Objective

Make compiled specializations safe to reuse: guard objects that verify
assumptions before dispatch, a content-addressed local cache with
integrity checking that fails closed, and recompilation budgets that
prevent specialization storms.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §6.4 (guard classes + policy 1-5), §17.6
   (cache key fields), §35 Epic 3 acceptance
3. `capture/fingerprint.py` + `capture/graph.py` (S09)

## Out of scope

- Tensor/dataframe-specific guard VALUES (S16/S17 supply them; this
  sprint defines the guard kinds and machinery using plain-Python and
  synthetic metadata). Remote cache (post-v0.1). Artifact container
  signing (S27).

## Tasks

### T1 — Guard model
- [ ] Do: `python/cobra_compiler/capture/guards.py` + native fast-path
  where trivial: guard kinds for callable identity (fingerprint),
  argument type, dtype, shape (exact + dim-wildcard), stride/layout
  flag, device, selected constant values, adapter/library version,
  semantic-mode flags (§6.4 list; model-identity guard kind declared
  but valued in S16). Guards serialize to a canonical, hashable form.
- Accept: each guard kind has pass/fail unit tests; serialized form is
  stable across processes (golden file test).

### T2 — Cache key + content-addressed store
- [ ] Do: cache key assembly per §17.6 (source fingerprint, captured
  constants, input guards, adapter versions, cobra revision, backend
  revision placeholder, GPU arch placeholder, semantic flags,
  cost-model version placeholder); SHA-256 content addressing;
  on-disk layout `.cobra/cache/<key>/{meta.json, module.mlirbc,
  guards.json}`; atomic writes (tmp+rename); integrity hash verified on
  EVERY load — mismatch = treat as miss + quarantine the entry +
  diagnostic (fail closed, §17.6).
- Accept: hit/miss/corruption unit tests (corruption test flips one
  byte); concurrent-writer test (two processes) leaves cache valid.

### T3 — Specialization dispatch + recompile budget
- [ ] Do: on call: evaluate fast guards → hit → dispatch; miss → look
  for compatible cached specialization → else recompile within budget
  (§6.4 policy 1-5): configurable max recompiles per region
  (conservative default), storm counter, and eager-fallback + warning
  when exceeded. Counters exposed for explain/telemetry.
- Accept: storm test — inputs alternating shapes exceed budget →
  permanent eager fallback + single clear diagnostic (not log spam);
  budget configurable via API arg.

### T4 — Cache CLI + microbenchmark
- [ ] Do: `cobra cache list` and `cobra cache prune` (size/age policy,
  §3.2); pyperf microbench for guard evaluation and cache lookup
  (feeds the §20.3-A suite later); record baseline numbers in the
  Session log.
- Accept: CLI works against a populated cache; bench runs and reports
  stable numbers (CoV documented).

## Validation

```bash
uv run pytest test/python/test_guards.py test/python/test_cache.py -q
uv run cobra cache list
uv run python benchmarks/micro/bench_guards.py
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted (Epic 3: hit, recompile-or-fallback, fail
      closed, storm limit — all demonstrated by tests)
- [ ] Guard + cache-key formats documented in
      `docs/reference/cache-format.md` (versioned)
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S12 uses guard failures as one graph-break/fallback trigger. S16/S17
register tensor/dataframe guard values through T1's kinds. S19 adds
cost-model version into the T2 key (field already reserved).

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
