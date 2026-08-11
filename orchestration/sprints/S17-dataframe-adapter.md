# S17 — Dataframe adapter (pandas / cuDF / Arrow)

| Field | Value |
|---|---|
| GitHub issue | #18 |
| Milestone | M3 — Integration & evidence |
| Depends on | S16 (done) |
| Hardware | **NVIDIA GPU required** (cuDF path) |
| Estimated sessions | 3-4 |
| Plan sections | §10.1-10.4, §35 Epic 6, §19.10 (subset) |

## Objective

Capture the §10.1 relational subset into `cobra.rel` nodes with dual
execution (pandas on CPU, cuDF on GPU), Arrow interchange, and strict
metadata fidelity — falling back to pandas rather than approximating
semantics (§10.4). This unlocks the dataframe→tensor residency win from
Experiment B as a product feature.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §10.1 (op list), §10.2 (backend policy),
   §10.3 (optimizations — read for shape, implement only fusion-safe
   basics), §10.4 (semantic hazards), §35 Epic 6
3. Adapter patterns from S16 (`adapters/torch/` as reference)
4. Experiment B writeup (`experimental/experiments/B/RESULTS.md`)

## Out of scope

- Substrait serialization (beta). Native CPU engine (beta). Predicate
  pushdown/join reordering beyond trivial projection pruning (§10.3
  full set arrives with S23 optimizer work where legal). Window ops,
  extension arrays (explicit fallback).

## Tasks

### T1 — `cobra.rel` minimal dialect + relational capture
- [ ] Do: add `cobra.rel` ops for the §10.1 subset (scan/read_parquet,
  project, filter, scalar-expr, assign, astype, fillna/dropna, groupby-
  agg {sum,mean,count,min,max}, merge/join (inner/left, supported key
  dtypes), sort, to_arrow/to_numpy/to_tensor, materialize) with schema
  attrs (names, dtypes, nullability, index kind); pandas-API capture
  via proxy DataFrame/Series wrapping the supported methods; anything
  else → `GB-PANDAS-UNSUPPORTED` fallback (S12 machinery).
- Accept: supported chains produce verified IR with schema metadata;
  unsupported method falls back cleanly mid-chain (test: capture →
  break → resume).

### T2 — Dual execution: pandas & cuDF
- [ ] Do: executors for rel regions: CPU = pandas; GPU = cuDF (pinned
  RAPIDS version → support-matrix.yaml). Placement chosen by explicit
  flag/hint for now (S19 cost model takes over). Schema guards (S11
  kinds) valued from real frames: column names/dtypes/nullability/
  index (§6.4 dataframe guard class).
- Accept: every supported op runs on both backends; guard mismatch
  (schema drift) triggers recompile-or-fallback per budget.

### T3 — Semantic hazard matrix (§10.4 → tests)
- [ ] Do: differential tests pandas-eager vs Cobra(CPU) vs Cobra(GPU)
  for: index preservation, duplicate keys, nullable int/bool dtypes,
  NaN-vs-null, categoricals, timezone-aware timestamps, stable sort
  flag, string/unicode, groupby-null handling, join duplicate keys,
  empty frames/columns/groups. Oracle compares values AND metadata
  (§19.10: "a dataframe with correct numbers and a wrong index is
  wrong"). Where cuDF semantics legitimately differ → op goes on the
  fallback list, not the approximation list (§10.4).
- Accept: matrix green; the fallback list is machine-readable
  (`adapters/dataframe/coverage.yaml` — Epic 6 acceptance).

### T4 — Arrow interchange + df→tensor path
- [ ] Do: `to_arrow()` via Arrow C Data Interface (zero-copy where
  legal); `to_tensor()`: cuDF→DLPack→torch on GPU (Experiment B path,
  now productized through the capture graph), pandas→numpy→torch on
  CPU; conversions are graph nodes with copy-accounting metadata
  (bytes, route) surfaced in explain.
- Accept: GPU path avoids host round-trip (assert via pointer device +
  transfer counters); values/dtype parity tests incl. nulls policy
  (documented: reject null→tensor unless fillna'd — explicit error).

### T5 — Explain + coverage reporting
- [ ] Do: explain output gains rel-region rendering: chosen backend,
  schema in/out, fallback reasons per §3.4 shape; `coverage.yaml`
  rendered into `docs/reference/dataframe-coverage.md` (generated,
  drift-checked in CI).
- Accept: explain snapshot for `parquet_feature_inference` shows rel
  region + backend + copies; coverage doc current.

## Validation

```bash
uv run pytest test/python/adapters/dataframe -q
uv run pytest test/Differential -q -m dataframe        # GPU host
uv run python examples/df_to_tensor_residency.py       # prints transfer bytes both routes
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted (Epic 6: declared matrix passes, metadata
      validated, unsupported returns to pandas without graph
      corruption)
- [ ] Coverage file + generated doc committed; RAPIDS pin recorded
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S18 formalizes the ownership/lifetime rules that T4 currently handles
with conservative syncs. S19 replaces T2's placement flag with the cost
model. The coverage.yaml format is reused by S24's corpus planning.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
