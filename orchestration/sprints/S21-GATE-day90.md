# S21 — GATE: day-90 go / narrow / stop

| Field | Value |
|---|---|
| Milestone | M3 — Integration & evidence (closes it) |
| Depends on | S20 (done) |
| Hardware | none (review; cheap re-checks allowed) |
| Estimated sessions | 1 |
| Plan sections | §29 (day-90 criteria), §28.1, §24.2 (route check) |
| Run with | `orchestration/prompts/P3-gate-review.md` |

## Objective

Decide with the human whether the integrated architecture earns the
v0.1 hardening investment (M4). The plan's day-90 criteria are explicit
and none of them is negotiable by enthusiasm: *"If these criteria fail,
the team must explicitly choose to stop, narrow, or redefine the target
market"* (§29).

## Evidence inputs

- `docs/benchmarks/day90-report.md` + `artifacts/{raw,analysis}/day90/`
  (S20)
- `docs/benchmarks/runtime-overhead.md` (S15)
- Differential/shadow status (S12→S19 test lanes, CI history)
- Sprint Session logs S16-S20 (known gaps, deferred issues)

## Gate checklist (each item: PASS/FAIL + evidence link)

From §29 day-90 decision criteria:

1. [ ] **Zero semantic divergence** in the qualification corpus
   (differential + shadow lanes green; no open wrong-code issue).
2. [ ] **≥70% of target operations or runtime weight captured** in at
   least one representative pipeline (explain node accounting).
3. [ ] **≥1 cross-library pipeline exceeds B1 by ≥15%** (CI excludes
   1.0x; oracle-passed; mechanism traced).
4. [ ] **≥1 pipeline eliminates a measurable transfer or
   materialization boundary** (S18 counters before/after).
5. [ ] **Scheduler overhead small enough to preserve measured gains**
   (S15 budget vs S20 numbers).
6. [ ] **Credible route to v0.1 gates within 12-16 weeks** — review M4
   sprint list (S22-S29) against known gaps; the route must name its
   risks.

## Procedure

1. Verify each item yourself (recompute CIs from raw data; spot-check
   traces; open the counter evidence). Write
   `docs/gates/day90-report.md`: criterion table, weaknesses,
   recommendation (go/narrow/stop; narrow options per §28.1).
2. **STOP — human decision required.**
3. On decision: D-NNN entry, tag `gate-day90`, ROADMAP + STATE update
   (go → S22; narrow/stop → P4-replan; M4 scope adjustments from
   checklist item 6 also go through P4).

## Definition of Done

- [ ] `docs/gates/day90-report.md` committed with human decision
- [ ] DECISIONS.md entry + `gate-day90` tag
- [ ] STATE.md advanced (or replan triggered)

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
