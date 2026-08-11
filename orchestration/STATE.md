# STATE — single source of truth

> Read me first. Update me last (every session). Keep me under ~80 lines:
> history belongs in sprint Session logs, not here.

**Last updated:** 2026-08-11 — S00 validation reopened: LICENSE is not verbatim canonical (T1 defect)

## Now

| Field | Value |
|---|---|
| Milestone | M0 — Thesis validation |
| Active sprint | S00 — Project bootstrap (`orchestration/sprints/S00-project-bootstrap.md`) |
| Sprint status | `in_progress` |
| Current task | T1 — repair `LICENSE` to match canonical https://llvm.org/LICENSE.txt |
| Branch | `sprint/S00-project-bootstrap` |
| Next action | Run `orchestration/prompts/P0-execute.md` in a fresh session |

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
| 2026-08-11 | S00 validation (P1) | All automated validation commands pass. Acceptance audit found T1 defect: `LICENSE` is not verbatim canonical (diff vs https://llvm.org/LICENSE.txt). Sprint reopened to fix T1; next is P0. |
| 2026-08-11 | S00 recovery (P2) | Found dirty working tree after a44e1e0 with uncommitted out-of-scope CI/tooling WIP. S00 validation still passes on a44e1e0 (`uv sync`, `./scripts/check.sh`, 80 READMEs, import smoke). Rescued WIP to `rescue/S00-2026-08-11`, reset `sprint/S00-project-bootstrap` to a44e1e0. Sprint remains `needs_validation`; next is P1. |
| 2026-08-11 | Harness review + rewrite (Devin) | Reviewed loop vs plan; rewrote worker layer to `devin -p` subprocesses; fixed gate detection, blocked-state policy, no-ack mailbox bug, uncommitted STATE advancement. |

## Notes for the next session

- S00 was reopened by Validator: T1 LICENSE is not verbatim canonical. Fix by
  replacing `LICENSE` with the full text from https://llvm.org/LICENSE.txt (or
  the approved project-specific equivalent), then re-run `./scripts/check.sh`
  and re-validate with P1.
- S00 is CPU-only and runs fine from any machine.
- The plan's §36 approval record is pending; the S05 gate collects the
  formal sign-offs. Proceeding through M0 is explicitly authorized by the
  owner (2026-08-10).
- Autonomous Orca loop harness is present on `sprint/S00-project-bootstrap`
  (`scripts/cobra_orca_loop.py`, wrapper, precheck).
- Security contact email remains a flagged placeholder in `SECURITY.md`.
- Linux + NVIDIA GPU host details still need to be recorded before S02.
- Uncommitted CI/npm tooling WIP from an unfinished session was rescued to
  `rescue/S00-2026-08-11`; the sprint branch is now clean at a44e1e0 and still
  `needs_validation`.
- Orca automation registered: `Cobra Autonomous Sprint Loop`
  (id `9bc2f963-7a94-46a7-b870-f23f3523cd43`), hourly trigger, enabled.
