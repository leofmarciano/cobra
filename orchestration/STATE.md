# STATE — single source of truth

> Read me first. Update me last (every session). Keep me under ~80 lines:
> history belongs in sprint Session logs, not here.

**Last updated:** 2026-08-11 — S02 unblocked; recovery done, branch recreated, resuming T0

## Now

|| Field | Value |
|---|---|---|
|| Milestone | M0 — Thesis validation |
|| Active sprint | S02 — Baseline workloads & B0/B1 report (`orchestration/sprints/S02-baseline-workloads.md`) |
|| Sprint status | `in_progress` |
|| Current task | T0 — Record the GPU host |
|| Branch | `sprint/S02-baseline-workloads` |
|| Next action | Run P0 (Executor) to complete T0 and continue S02 |

## Blockers

- (none)

## Human-input queue

Items an executor needs from the owner; answer by editing this list.

- [x] ~~Run `devin auth login`~~ — resolved 2026-08-11: owner confirmed the
      Orca automation environment authenticates fine; the "Not logged in"
      was an artifact of a sandboxed review shell only. Not a blocker.
- [ ] Security contact email for `SECURITY.md` (needed in S00-T1)
- [x] ~~Linux + NVIDIA GPU host details~~ — resolved 2026-08-11: this WSL
      session has direct access to an NVIDIA GeForce RTX 3080 (driver 591.86,
      compute cap 8.6, 10 GiB). CUDA toolkit presence to be verified by T0.

## Environment

|| Item | Value |
|---|---|---|
|| Orchestration host | WSL2 Ubuntu 24.04.1 LTS (this session) — native builds allowed; GPU available |
|| Dev/bench host | WSL2 Ubuntu 24.04.1 LTS / kernel 6.6.87.2-microsoft-standard-WSL2 / Intel Core i9-10900F (12 vCPU) / 15 GiB RAM |
|| GPU availability | NVIDIA GeForce RTX 3080, 10 GiB, driver 591.86, compute cap 8.6 (CUDA toolkit pending `nvcc` verification) |
|| Python toolchain | `uv` (to be pinned in S00) |
|| Remote | github.com/leofmarciano/cobra (do NOT push without human ask) |
|| Worker agent | Devin CLI headless (`devin -p`), spawned by `scripts/cobra_orca_loop.py`; default `--permission-mode dangerous` (owner-approved for unattended runs, D-004) |

## Last 3 sessions

|| Date | Session | Result |
|---|---|---|---|
|| 2026-08-11 | S02 executor (P0), T0 blocked | Booted and read context budget. GPU host now available (WSL2 + RTX 3080), but repo state contradicts itself: working tree on `main` while `STATE.md` declares branch `sprint/S02-baseline-workloads`; git history shows S02 branch already merged via PR #32 (`995e564`); `ROADMAP.md` ledger lists S02 as `not_started` while `STATE.md` lists `in_progress`. Per `AGENTS.md`/`P0-execute.md`, stopping for `P2-recovery.md`. |
|| 2026-08-11 | S01 Validator (P1) | Validated and closed S01. Re-ran all sprint validation commands, ran `./scripts/check.sh`, and found/fixed two CI gaps so the harness tests and mypy run in CI. Merged `sprint/S01-benchmark-harness` into `main` (9d4ec3d). Closed GitHub issue #2. Updated ROADMAP/STATE/LEARNINGS. Next: S02 T0 — record the Linux + NVIDIA GPU host. |
|| 2026-08-11 | S02 executor (P0), T0 | Booted S02, created branch `sprint/S02-baseline-workloads` from `main`, read context budget (plan §20.2, §20.3-D, §29 Days 1-10, §2.4, §33.2-33.4). Cannot run `cobra-bench doctor --strict` on macOS (no GPU; strict mode requires GPU metadata per §33.2). Recorded blocker: need owner-provided Linux + NVIDIA GPU host access details. No code changes. |

## Notes for the next session

- S01 is merged to `main` and done.
- S02 is the active sprint (GPU required). State contradiction resolved by
  operator: branch `sprint/S02-baseline-workloads` recreated, ROADMAP/STATE
  reconciled. Ready to execute T0.
- GPU host: WSL2 + RTX 3080 (driver 591.86, compute cap 8.6, 10 GiB).
  CUDA toolkit presence to be verified by T0.
- The harness has zero Cobra-internal dependencies and measures arbitrary Python
  callables via manifest entrypoints.
- The plan's §36 approval record is pending; the S05 gate collects the
  formal sign-offs. Proceeding through M0 is explicitly authorized by the
  owner (2026-08-10).
- Autonomous Orca loop harness is present on `main` (`scripts/cobra_orca_loop.py`,
  wrapper, precheck).
- Security contact email remains a flagged placeholder in `SECURITY.md`.
