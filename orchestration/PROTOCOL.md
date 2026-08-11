# PROTOCOL — Rules of the Cobra AI execution loop

This document defines how AI sessions cooperate to build Cobra without
losing context. It is written for models with ~300k-token context windows
that forget everything between sessions. The loop assumes **the filesystem
and git history are the only durable memory**.

## 1. Roles

| Role | Prompt | Purpose |
|---|---|---|
| Executor | `prompts/P0-execute.md` | Does sprint work (start or continue) |
| Validator | `prompts/P1-validate.md` | Independently verifies and closes a sprint |
| Recovery | `prompts/P2-recovery.md` | Reconciles inconsistent state |
| Gatekeeper | `prompts/P3-gate-review.md` | Runs go/narrow/stop gates with the human |
| Replanner | `prompts/P4-replan.md` | Modifies the roadmap after decisions |

The human operator opens a fresh AI session and pastes the appropriate
prompt. **Executor and Validator for the same sprint must be different
sessions** (fresh context) so validation is adversarial, not self-graded.

## 2. Sprint lifecycle

```
not_started → in_progress → needs_validation → done
                   ↑                |
                   +--- reopened ---+        (any state) → blocked
```

- Executor moves `not_started/in_progress → needs_validation` when every
  task checkbox is checked and self-validation commands pass.
- Only a Validator session may set `done` (recorded in ROADMAP.md ledger).
- `blocked` requires a written blocker in STATE.md naming what unblocks it.
- Gates (S05, S21, S29) additionally require explicit human sign-off
  recorded in DECISIONS.md.

## 3. Session lifecycle (every session, no exceptions)

### BOOT
1. Read `AGENTS.md`, `orchestration/STATE.md`, `orchestration/PROTOCOL.md`,
   active sprint file.
2. `git status` + `git log --oneline -10`. Working tree must be clean; if
   not, or if git disagrees with STATE.md, switch to Recovery.
3. Verify you are on the sprint branch (`sprint/S<NN>-<slug>`); create it
   from `main` if the sprint is starting fresh.
4. Announce: sprint ID, task you will work on, and a short plan.

### WORK
- Work top-down through unchecked tasks. One task at a time.
- TDD: failing test → implementation → green → refactor (plan §18.1).
- Commit after each completed task: `S<NN> T<k>: <imperative summary>`.
- Check the task checkbox in the sprint file in the same commit.
- Never leave the tree broken at a commit boundary.

### HANDOFF (mandatory, triggered by: sprint finished, ~80% context used,
### 3-strike escalation, or human ends session)
1. Append to the sprint file's **Session log**: date, what was completed,
   what is in progress, exact next step, surprises/decisions made.
2. Update `orchestration/STATE.md` (status, current task, next action,
   blockers).
3. If a durable lesson was learned (build quirk, API gotcha, flaky tool),
   append it to `orchestration/LEARNINGS.md`.
4. Commit: `S<NN>: session handoff`.
5. Output a 5-line summary for the human.

## 4. Escalation — the 3-strike rule

If the same error defeats 3 genuinely different attempts: stop, record the
blocker (STATE.md + Session log) with exact reproduction steps, and end the
session cleanly. Do not thrash. Do not disable the failing check.

## 5. Context budget rules

- Read only what the sprint's "Context budget" lists. The technical plan is
  referenced by section number (§) — read only those sections.
- Prefer `grep`/targeted reads over reading whole files.
- If you need something not listed, note the gap in the Session log (the
  sprint file's budget gets fixed by the Validator).
- If you feel lost or contradicted by the code: stop reading more files and
  switch to `prompts/P2-recovery.md`.

## 6. Git discipline

- Branch per sprint: `sprint/S<NN>-<slug>`. Small, frequent commits.
- `main` only receives merges from Validator sessions (`--no-ff`).
- Never force-push, never rebase published branches, never push to remote
  unless the human asks.
- Gates create annotated tags: `gate-day30`, `gate-day90`, `v0.1.0-preview`.

## 7. Engineering rules inherited from the plan (always apply)

- Conservative-by-default: unknown effects are barriers; fallback must
  preserve observable Python behavior (plan §6.5).
- Every optimization needs: semantic contract, failing test, differential
  test, IR regression test, benchmark hypothesis, flag/rollback (plan §18.1).
- Benchmarks follow §33; the anti-patterns in §33.11 invalidate results.
- No new third-party dependency without recording it in the sprint log and
  DECISIONS.md (license + version pin). Prefer versions ≥7 days old.
- Native work (C++/CMake/CUDA) runs in the dev container / Linux GPU host,
  never raw on macOS.

## 8. File ownership (prevents drift)

| File | Written by | When |
|---|---|---|
| STATE.md | every session | end of session (and when blocked) |
| Sprint file checkboxes + Session log | Executor | during/end of session |
| ROADMAP.md ledger row | Validator / Gatekeeper | sprint closure / gate |
| LEARNINGS.md | any session | append-only |
| DECISIONS.md | Gatekeeper + human | gates, replans, dependency adds |
| sprints/*.md task definitions | Replanner only | after a recorded decision |

## 9. Session size guidance

A sprint is sized for 1-4 executor sessions. Stop a session at a natural
task boundary rather than mid-task. Restarting costs one BOOT (~5 minutes);
a corrupted handoff costs a Recovery session (~an hour). Hand off early.
