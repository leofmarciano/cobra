# STATE — single source of truth

> Read me first. Update me last (every session). Keep me under ~80 lines:
> history belongs in sprint Session logs, not here.

**Last updated:** 2026-08-11 — S00 T1 LICENSE repaired; sprint complete, awaiting validation

## Now

| Field | Value |
|---|---|
| Milestone | M0 — Thesis validation |
| Active sprint | S00 — Project bootstrap (`orchestration/sprints/S00-project-bootstrap.md`) |
| Sprint status | `needs_validation` |
| Current task | T1 — repaired; all tasks complete |
| Branch | `sprint/S00-project-bootstrap` |
| Next action | Run `orchestration/prompts/P1-validate.md` in a fresh session |

## Blockers

- (none)

## Human-input queue

Items an executor needs from the owner; answer by editing this list.

- [x] ~~Run `devin auth login`~~ — resolved 2026-08-11: owner confirmed the
      Orca automation environment authenticates fine; the "Not logged in"
      was an artifact of a sandboxed review shell only. Not a blocker.
- [ ] Security contact email for `SECURITY.md` (needed in S00-T1)
- [ ] Linux + NVIDIA GPU host details (hostname/access, GPU model, driver,
      CUDA toolkit) — needed no later than S02. Owner confirmed hardware
      exists (2026-08-10).

## Environment

| Item | Value |
|---|---|
| Orchestration host | macOS (owner laptop) — docs/git only, no native builds |
| Dev/bench host | **TBD** — first GPU sprint must record: OS, kernel, CPU, RAM, GPU, driver, CUDA toolkit |
| GPU availability | Confirmed available by owner (2026-08-10) |
| Python toolchain | `uv` (to be pinned in S00) |
| Remote | github.com/leofmarciano/cobra (do NOT push without human ask) |
| Worker agent | Devin CLI headless (`devin -p`), spawned by `scripts/cobra_orca_loop.py`; default `--permission-mode dangerous` (owner-approved for unattended runs, D-004) |

## Last 3 sessions

| Date | Session | Result |
|---|---|---|
| 2026-08-11 | S00 executor (P0) | Repaired `LICENSE` to match https://llvm.org/LICENSE.txt verbatim (only project-name header changed to "The Cobra Project"). `diff -u` against the canonical file shows exactly one line. All S00 validation commands pass (`uv sync`, `./scripts/check.sh`, 80 READMEs, import smoke). Sprint status set to `needs_validation`; next is P1. |
| 2026-08-11 | S00 recovery #2 (P2) | Found dirty tree again on `sprint/S00-project-bootstrap` at 6d53308 — same anti-pattern as the prior same-day recovery (out-of-scope CI/npm tooling WIP), T1 (LICENSE) still untouched. Verified 6d53308 passes all S00 validation commands. Rescued WIP to `rescue/S00-2026-08-11-0037`, reset sprint branch to 6d53308. Unchecked T1 box (defect confirmed, not just unverified). Sprint remains `in_progress`/T1; next is P0 — actually fix LICENSE. |
| 2026-08-11 | S00 validation (P1) | All automated validation commands pass. Acceptance audit found T1 defect: `LICENSE` is not verbatim canonical (diff vs https://llvm.org/LICENSE.txt). Sprint reopened to fix T1; next is P0. |

## Notes for the next session

- S00 is complete and awaiting validation: run `orchestration/prompts/P1-validate.md`
  in a fresh session.
- S00 is CPU-only and runs fine from any machine.
- The plan's §36 approval record is pending; the S05 gate collects the
  formal sign-offs. Proceeding through M0 is explicitly authorized by the
  owner (2026-08-10).
- Autonomous Orca loop harness is present on `sprint/S00-project-bootstrap`
  (`scripts/cobra_orca_loop.py`, wrapper, precheck).
- Security contact email remains a flagged placeholder in `SECURITY.md`.
- Linux + NVIDIA GPU host details still need to be recorded before S02.
