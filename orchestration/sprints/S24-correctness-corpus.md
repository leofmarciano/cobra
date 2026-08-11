# S24 — 50-program corpus, property & metamorphic testing

| Field | Value |
|---|---|
| Milestone | M4 — v0.1 hardening & release |
| Depends on | S23 (done) |
| Hardware | **NVIDIA GPU required** |
| Estimated sessions | 3-4 |
| Plan sections | §19.5-19.7, §19.9-19.10, §24.2 (correctness gates), §35 Epic 12 (corpus part) |

## Objective

Scale correctness evidence to v0.1-gate volume: 50 curated programs,
Hypothesis-driven property suites for tensors and dataframes, the
metamorphic relation suite, and automation that turns every failure into
a permanent minimized regression. Target: the §24.2 requirement of
"at least 25,000 generated property and differential cases across
qualification runs" becomes routinely reachable.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §19.5 (differential comparisons), §19.6
   (property dimensions), §19.7 (metamorphic relations), §19.9/§19.10
   (matrices), §24.2 correctness-gate numbers
3. `test/Differential/corpus/` (S12) + adapter coverage files
   (S16/S17)

## Out of scope

- Fuzzing of parsers/binary surfaces (S25). Training/autograd cases.
  CI wiring beyond profiles (S25 finalizes lanes). Beta-scale numbers
  (250k cases — only the 25k v0.1 bar matters here).

## Tasks

### T1 — Corpus 15→50
- [ ] Do: extend `test/Differential/corpus/` to 50 programs per the
  v0.1 supported surface, distributed roughly: 12 tensor-centric, 12
  dataframe-centric, 10 mixed df→tensor, 6 mutation/alias traps, 5
  exception/warning paths, 5 RNG/fallback/guard-storm cases. Each
  program: docstring stating the defended rule, eager+captured+shadow
  execution, metadata-aware oracles (§19.5 comparison list incl.
  dataframe index/nulls/categories and tensor dtype/shape/stride-where-
  promised/device).
- Accept: 50/50 green with optimizer ON and OFF; corpus README
  categorizes programs (machine-readable index).

### T2 — Property-based tensor suite
- [ ] Do: Hypothesis strategies for §19.6 tensor dimensions: shapes
  (incl. zero-dim + empty), strides (contiguous/transposed/sliced),
  dtypes, extreme values (NaN/inf/signed-zero/denormals), shared-
  storage/view aliasing; each supported op family gets a property test
  comparing Cobra vs eager under per-family tolerance policy (§19.5
  "not a single global tolerance"). Profiles: `ci` (fast), `nightly`
  (large), `qualification` (gate-scale).
- Accept: `ci` profile green; failure auto-persists minimized repro
  into `test/Differential/regressions/` and re-runs from there (§19.6
  requirement — demonstrate with a seeded intentional bug on a branch).

### T3 — Property-based dataframe suite
- [ ] Do: same for §19.6/§19.10 dataframe dimensions: nullable columns,
  duplicate keys/indexes, empty groups, tz-aware timestamps,
  categoricals, unicode, schema drift; metadata equality in the oracle
  (values AND index AND dtypes AND category metadata).
- Accept: `ci` green; ≥3 real bugs-or-confirmations documented in
  Session log (property suites that find nothing on first contact are
  usually too weak — investigate and state why if so).

### T4 — Metamorphic suite
- [ ] Do: implement §19.7 relations as parameterized tests over corpus
  programs: no-op insertion invariance, independent-source-order
  invariance (pure), batch split+concat = whole-batch (declared ops),
  CPU-vs-GPU within contract, capture-without-optimization = eager,
  serial-vs-parallel scheduler agreement, cache-miss = cache-hit,
  optimizer-on = optimizer-off.
- Accept: suite green; each relation runs against ≥10 corpus programs.

### T5 — Case-count accounting
- [ ] Do: qualification profile runner that counts generated cases
  across property+differential suites and emits
  `artifacts/qualification/case-count.json` (schema: suite → cases →
  pass/fail) — S28 needs ≥25,000 with zero unexplained divergence.
  Run it once fully on the GPU host and record the number.
- Accept: counter artifact committed; ≥25k demonstrated OR the gap +
  scaling plan stated plainly in the Session log for S28.

## Validation

```bash
uv run pytest test/Differential -q
uv run pytest test/property --hypothesis-profile=ci -q
uv run pytest test/metamorphic -q
uv run python scripts/qualification-count.py --profile qualification --dry-run
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; 50-program corpus green both optimizer states
- [ ] Regression-persistence mechanism demonstrated
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S25 adds the adversarial layer (fuzz/sanitizers/injection) on top of
this corpus; S28 runs the `qualification` profile for the gate numbers.
The corpus index format is the base for the beta 200-program expansion.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
