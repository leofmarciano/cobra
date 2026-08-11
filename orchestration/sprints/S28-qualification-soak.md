# S28 — v0.1 qualification (soak + gates evidence)

| Field | Value |
|---|---|
| Milestone | M4 — v0.1 hardening & release |
| Depends on | S24, S25, S27 (done) |
| Hardware | **NVIDIA GPU required** (frozen bench host, multi-day) |
| Estimated sessions | 3-4 (plus unattended soak/fuzz wall-time) |
| Plan sections | §24.2 (ALL gates), §19.19, §33, §35 Epic 12 |

## Objective

Assemble the complete v0.1 gate dossier: run the 24h soak, the
qualification-scale correctness campaign, the frozen benchmark
qualification against every §24.2 performance number, and the product
gate checks — producing `docs/qualification/v0.1/` with evidence for
every line the S29 gate will judge. Gaps are findings, not failures:
they get fixed, descoped-with-flags, or honestly listed.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §24.2 in FULL (correctness, performance,
   product gates), §19.19 (soak metrics), §33.9 (release comparison)
3. `artifacts/qualification/` (S24 case counts, S25 fuzz ledger),
   S27 wheels, S20 day90 suite/report as baseline history

## Out of scope

- Fixing large defects found here (each becomes a defect sprint via
  P4-replan if >1 session of work; small fixes allowed inline with
  tests). Publishing anything (S29). Beta gates.

## Tasks

### T1 — 24-hour soak (§19.19 / §24.2)
- [ ] Do: soak harness: repeated compile+execute across the workload
  set with varying inputs, tracking host/device memory, fds,
  streams/events, cache growth, compile latency drift, divergence,
  queue depth; run 24h on the GPU host; analyze: no monotonic leak,
  steady-state growth ≤1% over final 80% (bounded caches accounted),
  ≥100k successful executions without divergence/deadlock/exhaustion.
- Accept: soak report + raw telemetry committed; every §24.2 soak
  bullet explicitly PASS/FAIL.

### T2 — Correctness campaign at gate scale
- [ ] Do: run: 50-program corpus (both optimizer states, shadow spot-
  checks), property+differential `qualification` profile until the
  ≥25k generated-case bar is exceeded (S24 counter), fuzz ledger sum
  ≥10M execs (schedule campaigns to close any gap; §24.2), full
  sanitizer matrix (asan-ubsan, tsan, compute-sanitizer set) at the
  qualification commit.
- Accept: `docs/qualification/v0.1/correctness.md` with numbers +
  artifact links; zero known Sev1/Sev2 in enabled features (§24.1) —
  any found: fix or disable-by-default + list.

### T3 — Performance qualification (frozen host)
- [ ] Do: full §33 protocol on the day90 suite (B0/B1/B2-where-present/
  B3, wheel-installed build): evaluate EVERY §24.2 performance gate:
  ≥1.25x geomean warm over B0; ≥3 pipelines ≥1.10x over B1 (CI excludes
  1.00x); no Cobra-labeled-profitable pipeline >5% slower than B1
  beyond noise (else cost model must fall back — fix or flag);
  ≥2 pipelines with ≥30% transfer-byte reduction; ≥2 pipelines with
  measured overlap and ≥10% critical-path gain; fallback-only overhead
  ≤5% p50; warm latency includes cache-hit load + guards; break-even
  ≤100 runs for ≥half the repeated-server-style workloads.
- Accept: `docs/qualification/v0.1/performance.md` — a table of all
  eight gate lines with measured values, CIs, and PASS/FAIL. (Note:
  the suite is 3 pipelines; where a gate speaks of "≥3 pipelines",
  all three must qualify — if that is unrealistic, the finding goes to
  S29 with a recommendation: extend suite (new sprint) or narrow the
  claim. Do not quietly reinterpret the gate.)
- Note: if workload count vs gate arithmetic requires suite expansion,
  raise it EARLY in the Session log — S29 may need a decision.

### T4 — Product gates
- [ ] Do: verify each §24.2 product line: wheel clean-install on
  reference env (S27 battery, re-run at this commit); actionable
  diagnostics for every corpus graph break (S26 audit re-run);
  one-command benchmark report (`cobra benchmark`); one-command
  disable (env var/config documented + tested); docs complete
  (install/first-pipeline/explain/benchmark/fallback/troubleshooting);
  benchmark raw data + reproduction scripts publishable; license/
  notices/SBOM/security policy present.
- Accept: `docs/qualification/v0.1/product.md` checklist with evidence.

### T5 — Dossier + release-candidate freeze
- [ ] Do: `docs/qualification/v0.1/README.md` — master index: every
  §24.2 gate → PASS/FAIL → evidence path; known-issues list with
  severities (§24.1); freeze the RC: exact commit + wheel hashes
  recorded (S29 promotes THESE artifacts without rebuilding, §21.5).
- Accept: dossier complete; no gate line left unmeasured; RC hashes
  recorded.

## Validation

```bash
uv run python scripts/qualification-count.py --verify-thresholds
uv run python scripts/fuzz-ledger-report.py --min-execs 10000000
uv run cobra-bench compare --candidate artifacts/analysis/v0.1-rc/summary.json \
  --baseline artifacts/analysis/day90/summary.json --policy benchmarks/policies/release-v0.1.yaml
test -f docs/qualification/v0.1/README.md
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; dossier indexes every §24.2 gate with
      evidence; RC artifacts frozen by hash
- [ ] All findings triaged (fixed / disabled-by-default / listed)
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S29 judges the dossier. Anything ambiguous here costs a gate round-trip
— over-document rather than under-document.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
