# STATE — single source of truth

> Read me first. Update me last (every session). Keep me under ~80 lines:
> history belongs in sprint Session logs, not here.

**Last updated:** 2026-08-11 — harness review + rewrite to Devin-only workers (Devin)

## Now

| Field | Value |
|---|---|
| Milestone | M0 — Thesis validation |
| Active sprint | S00 — Project bootstrap (`orchestration/sprints/S00-project-bootstrap.md`) |
| Sprint status | `not_started` |
| Current task | T1 |
| Branch | `main` (create `sprint/S00-project-bootstrap` at BOOT) |
| Next action | Open a fresh session, paste `orchestration/prompts/P0-execute.md` |

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
| 2026-08-11 | Harness review + rewrite (Devin) | Reviewed loop vs plan; rewrote worker layer to `devin -p` subprocesses (Orca worker-start is claude/codex-only); fixed gate detection, blocked-state policy, no-ack mailbox bug, uncommitted STATE advancement. Found blocker: `devin auth login` needed. |
| 2026-08-10 | Sprint issues + labels (Devin) | Created 30 GitHub issues (#1-#30) for S00-S29, labels `sprint`/`milestone-M*`/`gate`, linked from sprint files and ROADMAP.md. |
| 2026-08-10 | Autonomous loop harness (Devin) | Added scripts/cobra_orca_loop.py + wrapper/precheck; branch sprint/S00-project-bootstrap. Sprint S00 still not_started. |

## Notes for the next session

- This project has NO code yet — only `COBRA_TECHNICAL_PLAN.md` (the
  constitution) and this orchestration layer.
- S00 is CPU-only and runs fine from any machine.
- The plan's §36 approval record is pending; the S05 gate collects the
  formal sign-offs. Proceeding through M0 is explicitly authorized by the
  owner (2026-08-10).
- Autonomous Orca loop harness added on branch `sprint/S00-project-bootstrap`
  (`scripts/cobra_orca_loop.py`, wrapper, precheck). The active sprint is
  still `not_started`; run P0 manually or enable the automation to begin S00.
- Orca automation registered: `Cobra Autonomous Sprint Loop`
  (id `9bc2f963-7a94-46a7-b870-f23f3523cd43`), hourly trigger, enabled.
- GitHub issues created for S00-S29 (#1-#30). Sprint files and ROADMAP.md link
  to them; labels: `sprint`, `milestone-M0..M4`, `gate` for gates.
