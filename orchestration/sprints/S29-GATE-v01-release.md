# S29 — GATE: v0.1 release review

| Field | Value |
|---|---|
| Milestone | M4 — v0.1 hardening & release (closes it) |
| Depends on | S28 (done) |
| Hardware | none (review; verification re-runs allowed) |
| Estimated sessions | 1-2 |
| Plan sections | §24.2, §30.4, §21.5, §20.10 |
| Run with | `orchestration/prompts/P3-gate-review.md` |

## Objective

Decide with the human whether v0.1.0-preview ships. The standard is
§30.4 (Definition of Done for a release) applied to the §24.2 gates:
the qualified binaries ARE the released binaries, known issues are
public and specific, and no performance claim outruns its evidence.

## Evidence inputs

- `docs/qualification/v0.1/` dossier (S28) — the primary artifact
- RC hashes + wheels (S28-T5)
- Open defect list / disabled-features list
- ROADMAP + Session logs for anything deferred with a flag

## Gate checklist

1. [ ] Every §24.2 **correctness** gate line: PASS with evidence (zero
   known Sev1/Sev2 in enabled features; corpus/property/fuzz/sanitizer
   /soak numbers met).
2. [ ] Every §24.2 **performance** gate line: PASS, or the specific
   narrowed claim is documented for the release notes (no silent
   reinterpretation — any narrowing is a human decision here).
3. [ ] Every §24.2 **product** gate line: PASS (install, diagnostics,
   one-command benchmark/disable, docs, raw-data publication,
   license/SBOM/security).
4. [ ] §30.4 release DoD: RC binaries = qualified binaries; known
   issues public + specific; support matrix published; rollback path
   tested (feature-disable drill re-run); install+tutorial tested by a
   session that did not implement them (a fresh validator session
   counts).
5. [ ] Release notes draft: honest §20.10-style reporting — wins,
   regressions, unsupported cases, raw-data links.

## Procedure

1. Audit the dossier line-by-line; re-run spot verifications (one
   corpus lane, one benchmark comparison, wheel-hash check). Write
   `docs/gates/v01-release-report.md` with the checklist + release
   recommendation (ship / fix-first list / narrow claims).
2. **STOP — human decision required** (this includes: publish to PyPI
   or GitHub-releases only; announce or quiet release).
3. On SHIP: D-NNN entry; tag `v0.1.0-preview` on the RC commit;
   promote the FROZEN artifacts (no rebuild, §21.5); publish per the
   human's channel decision (push/publish only with explicit human
   go); update ROADMAP (M4 done) and STATE.
4. Post-release: run a retrospective — append loop-level lessons to
   LEARNINGS.md; then next action = `P4-replan.md` to expand M5+ (beta)
   from `sprints/POST-V01-ROADMAP.md` using everything learned.

## Definition of Done

- [ ] `docs/gates/v01-release-report.md` committed with human decision
- [ ] On ship: tag exists, artifacts promoted unmodified, notes
      published; on hold: fix-list turned into sprints via P4
- [ ] Retrospective appended to LEARNINGS.md
- [ ] STATE.md advanced (next: beta replan)

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
