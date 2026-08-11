# S26 — CLI & developer experience

| Field | Value |
|---|---|
| Milestone | M4 — v0.1 hardening & release |
| Depends on | S23 (done; runs after S25 in ledger order) |
| Hardware | CPU-only (GPU spot-checks for doctor) |
| Estimated sessions | 2-3 |
| Plan sections | §3.2, §3.4, §17.2-17.4, §19.17, §35 Epic 11 |

## Objective

Make Cobra usable by a stranger: the full v0.1 CLI (`run / explain /
benchmark / doctor / cache / trace-export`), explain as a first-class
product (§17.2: "not a debug afterthought"), configuration precedence,
and executable documentation. Epic 11's bar: *"a new engineer can
install and run the tutorial from a clean environment."*

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §3.2 (CLI list), §3.4 (explain content),
   §17.2 (explain questions), §17.3 (config precedence), §17.4 (modes
   table), §19.17 (doc tests), §35 Epic 11
3. Existing CLI stubs (S10/S11), explain internals (S10/S17/S19/S23),
   reason registry (S12)

## Out of scope

- `cobra build`/AOT artifacts (post-v0.1). Fleet/telemetry (§22.5 —
  v0.1 ships telemetry OFF and without a collector). Windows/macOS
  product support.

## Tasks

### T1 — CLI consolidation
- [ ] Do: one `cobra` entry point with subcommands: `run app.py [--mode
  --target --math --fallback]`, `explain module:fn --inputs …`,
  `benchmark module:fn --baseline=eager` (wraps cobra-bench),
  `doctor [--strict]` (env + GPU + framework matrix check vs
  support-matrix.yaml), `cache list|prune`, `trace app.py --output
  trace.json` (schedule/timeline export from S13-T5). Exit codes and
  `--json` output for every command (machine-readable, §3.4).
- Accept: CLI integration tests per subcommand; `--help` snapshots
  drift-checked against docs (§19.17: "compared to generated command
  definitions").

### T2 — Explain, finished
- [ ] Do: explain must answer all ten §17.2 questions: captured
  regions, fallbacks+why (reason registry), alias hazards, effects,
  concurrent branches, per-node device+why (cost numbers), remaining
  transfers (S18 counters), kernels/vendor libs chosen, guards, and
  break-even estimate (S19). Text format per §3.4 sample; JSON schema
  versioned (`docs/reference/explain-schema.md` updated).
- Accept: snapshot tests on the three workloads answering all ten
  questions; JSON validates against its published schema.

### T3 — Configuration precedence
- [ ] Do: implement §17.3 chain fully: API args > CLI flags >
  `cobra.toml` > env vars > defaults; `[project]/[target]/[optimizer]/
  [cache]/[diagnostics]` sections per the §17.3 example; §17.4 modes
  (`safe` default, `performance`, `deterministic`, `debug`, `shadow`)
  wired to real flag sets; fast-math NEVER implied by performance
  (§17.4 — test this explicitly).
- Accept: precedence matrix test (each layer overriding the next);
  mode→flags table documented + tested; invalid config = located error.

### T4 — Documentation set
- [ ] Do: `docs/guides/`: installation, first-pipeline tutorial (the
  §24.2 product-gate list: install → compile → explain → benchmark →
  fallback → troubleshooting), fallback/graph-break guide (every
  registry reason gets an anchor + remediation), annotations guide
  (S22-T3 API), configuration reference (generated from the config
  model). Every code snippet executes in CI (§19.17) via a doc-test
  runner.
- Accept: doc-test lane green; tutorial runs end-to-end scripted
  (`scripts/run-tutorial.sh`) on a clean venv.

### T5 — Diagnostics quality pass
- [ ] Do: audit every graph break raised by the 50-program corpus:
  message actionable? source span correct? remediation real? (Epic 11:
  "every qualification graph break has a useful message"). Fix the
  weak ones; add a lint test asserting every registry entry has
  docs anchor + remediation text.
- Accept: corpus break-message audit table committed
  (`docs/reference/graph-break-audit.md`); lint test green.

## Validation

```bash
uv run pytest test/python/cli -q
uv run cobra doctor
uv run cobra explain examples/two_node_dag.py:pipeline --json | \
  uv run python scripts/validate-explain-schema.py
./scripts/run-tutorial.sh          # clean venv, CPU-only path
uv run pytest test/docs -q         # executable snippets
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted (Epic 11 acceptance in full)
- [ ] Explain answers all ten §17.2 questions with real data
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S27 packages this CLI into wheels (entry points already console-script
based). S28 uses `cobra doctor --strict` + the tutorial as product-gate
evidence.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
