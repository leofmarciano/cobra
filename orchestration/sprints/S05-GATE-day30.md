# S05 — GATE: day-30 go / narrow / stop

| Field | Value |
|---|---|
| GitHub issue | #6 |
| Milestone | M0 — Thesis validation (closes it) |
| Depends on | S04 (done) |
| Hardware | none (review only; cheap re-checks allowed) |
| Estimated sessions | 1 |
| Plan sections | §29 (day-30 review), §23 Phase 0 exit criteria, §28.1, §36 |
| Run with | `orchestration/prompts/P3-gate-review.md` |

## Objective

Decide — with the human — whether the Cobra thesis survived contact with
reality. The plan is explicit: *"If this gate fails, do not build a
general compiler"* (§23). This gate also freezes the semantic charter,
which every later sprint tests against.

## Evidence inputs

- `docs/benchmarks/phase0-baseline.md` (S02)
- `docs/benchmarks/phase0-tracer-findings.md` (S03)
- `docs/benchmarks/phase0-experiments.md` + per-experiment RESULTS (S04)
- `docs/decisions/ADR-0005-semantic-charter.md` (S00 draft)
- `artifacts/analysis/**` raw statistics

## Gate checklist (each item: PASS/FAIL + evidence link)

Derived from §23 Phase 0 exit criteria and §29 day-30 review:

1. [ ] ≥1 experiment shows a **statistically valid ≥15% improvement over
   B1** (bootstrap CI excludes 1.0x; oracle passed on every sample), OR a
   credible profiler-backed route to that result is documented.
2. [ ] ≥2 optimization opportunities identified that are **unavailable to
   a tensor-only compiler** (cross-library: scheduling, residency,
   whole-program view) — from S03/S04 evidence.
3. [ ] **Zero semantic mismatches** in the prototype corpus (oracles,
   exception-order test in Exp A, dataframe metadata checks in Exp B).
4. [ ] Every measured speedup is **explained by a profiler trace**
   (mechanism named; no unexplained wins — §18.6).
5. [ ] Semantic charter (ADR-0005) is complete, internally consistent,
   and ready to freeze (all six areas testable).
6. [ ] §36 approval items reviewed with the human (adapted solo-owner):
   narrow v0.1 scope, charter, B1-as-mandatory-baseline, license,
   stop conditions, "no performance result overrides a correctness
   failure".

## Procedure

1. Verify each checklist item YOURSELF (re-open artifacts; re-run cheap
   stats checks). Produce `docs/gates/day30-report.md` with the
   criterion table, weaknesses, and recommendation (go/narrow/stop).
   For `narrow`, propose 2-3 options from §28.1 (e.g., pipeline
   scheduler only; residency planner only; profiler/diagnostics
   product).
2. **STOP — ask the human for the decision.**
3. On decision: flip ADR-0005 to `accepted` (if go), record D-NNN in
   DECISIONS.md, tag `gate-day30`, update ROADMAP ledger + STATE.md
   (go → S06; narrow/stop → next action = P4-replan).

## Definition of Done

- [ ] `docs/gates/day30-report.md` committed with human decision recorded
- [ ] DECISIONS.md entry + `gate-day30` tag exist
- [ ] Charter frozen (or replan triggered)
- [ ] STATE.md advanced accordingly

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
