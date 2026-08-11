# STATE — single source of truth

> Read me first. Update me last (every session). Keep me under ~80 lines:
> history belongs in sprint Session logs, not here.

**Last updated:** 2026-08-10 — orchestration setup session (Devin)

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

## Last 3 sessions

| Date | Session | Result |
|---|---|---|
| 2026-08-10 | Orchestration setup (Devin) | Created loop docs, 30 sprint files, 5 prompts. No product code written. |

## Notes for the next session

- This project has NO code yet — only `COBRA_TECHNICAL_PLAN.md` (the
  constitution) and this orchestration layer.
- S00 is CPU-only and runs fine from any machine.
- The plan's §36 approval record is pending; the S05 gate collects the
  formal sign-offs. Proceeding through M0 is explicitly authorized by the
  owner (2026-08-10).
