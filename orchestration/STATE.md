# STATE — single source of truth

> Read me first. Update me last (every session). Keep me under ~80 lines:
> history belongs in sprint Session logs, not here.

**Last updated:** 2026-08-11 — S00 project bootstrap completed (Executor)

## Now

| Field | Value |
|---|---|
| Milestone | M0 — Thesis validation |
| Active sprint | S00 — Project bootstrap (`orchestration/sprints/S00-project-bootstrap.md`) |
| Sprint status | `needs_validation` |
| Current task | — |
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
| 2026-08-11 | S00 project bootstrap (Executor) | Completed T1–T6: governance docs, repository skeleton §16.1, Python packaging (cobra-compiler, Python 3.13), ADR template + ADR-0001..0005, lint CI + local check script. Validation passes: `uv sync`, `./scripts/check.sh`, READMEs tracked, import smoke test. |
| 2026-08-11 | Harness review + rewrite (Devin) | Reviewed loop vs plan; rewrote worker layer to `devin -p` subprocesses; fixed gate detection, blocked-state policy, no-ack mailbox bug, uncommitted STATE advancement. |
| 2026-08-10 | Sprint issues + labels (Devin) | Created 30 GitHub issues (#1-#30) for S00-S29, labels `sprint`/`milestone-M*`/`gate`, linked from sprint files and ROADMAP.md. |

## Notes for the next session

- S00 is complete and awaiting Validator review (P1). All six tasks pass
  the sprint validation commands from a clean checkout.
- S00 is CPU-only and runs fine from any machine.
- The plan's §36 approval record is pending; the S05 gate collects the
  formal sign-offs. Proceeding through M0 is explicitly authorized by the
  owner (2026-08-10).
- Autonomous Orca loop harness is present on `sprint/S00-project-bootstrap`
  (`scripts/cobra_orca_loop.py`, wrapper, precheck).
- Security contact email remains a flagged placeholder in `SECURITY.md`.
- Linux + NVIDIA GPU host details still need to be recorded before S02.
- Orca automation registered: `Cobra Autonomous Sprint Loop`
  (id `9bc2f963-7a94-46a7-b870-f23f3523cd43`), hourly trigger, enabled.
