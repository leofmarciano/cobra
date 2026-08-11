# STATE — single source of truth

> Read me first. Update me last (every session). Keep me under ~80 lines:
> history belongs in sprint Session logs, not here.

**Last updated:** 2026-08-11 — S02 booted; blocked on Linux + NVIDIA GPU host details

## Now

|| Field | Value |
|---|---|---|
|| Milestone | M0 — Thesis validation |
|| Active sprint | S02 — Baseline workloads & B0/B1 report (`orchestration/sprints/S02-baseline-workloads.md`) |
|| Sprint status | `blocked` |
|| Current task | T0 — Record the GPU host |
|| Branch | `sprint/S02-baseline-workloads` |
|| Next action | Provide Linux + NVIDIA GPU host details, then rerun `orchestration/prompts/P0-execute.md` |

## Blockers

- S02-T0 cannot run on this macOS orchestration host. Need Linux + NVIDIA GPU
  host access (hostname/SSH, GPU model, driver version, CUDA toolkit) to run
  `cobra-bench doctor --strict`, record `artifacts/environment/primary-host.json`,
  and fill the Environment table below.

## Human-input queue

Items an executor needs from the owner; answer by editing this list.

- [x] ~~Run `devin auth login`~~ — resolved 2026-08-11: owner confirmed the
      Orca automation environment authenticates fine; the "Not logged in"
      was an artifact of a sandboxed review shell only. Not a blocker.
- [ ] Security contact email for `SECURITY.md` (needed in S00-T1)
- [ ] Linux + NVIDIA GPU host details (hostname/SSH access, GPU model, driver
      version, CUDA toolkit) — blocking S02-T0. Owner confirmed hardware exists
      (2026-08-10); access details still needed.

## Environment

|| Item | Value |
|---|---|---|
|| Orchestration host | macOS (owner laptop) — docs/git only, no native builds |
|| Dev/bench host | **TBD** — first GPU sprint must record: OS, kernel, CPU, RAM, GPU, driver, CUDA toolkit. Currently blocked waiting for owner-provided access details. |
|| GPU availability | Confirmed available by owner (2026-08-10); access details pending |
|| Python toolchain | `uv` (to be pinned in S00) |
|| Remote | github.com/leofmarciano/cobra (do NOT push without human ask) |
|| Worker agent | Devin CLI headless (`devin -p`), spawned by `scripts/cobra_orca_loop.py`; default `--permission-mode dangerous` (owner-approved for unattended runs, D-004) |

## Last 3 sessions

|| Date | Session | Result |
|---|---|---|---|
|| 2026-08-11 | S01 executor (P0), T5+T6 | Implemented full `cobra-bench` CLI (`doctor`, `verify`, `run`, `analyze`, `compare`), `cobra_bench.runner` (entrypoint resolution, oracle factory, warm timing, cold subprocess placeholder, sample recording), `cobra_bench.compare` (threshold check between `summary.json` files), and `cobra_bench.guardrails` (mixed-phase refusal, input-fingerprint consistency, <30 sample warning, `--no-oracle` opt-out with loud warning). Extended manifest/stats for input fingerprints and phase. 34 new TDD tests; `uv run pytest benchmarks/harness -q` (120 passed), `mypy --strict` clean, ruff clean, sprint validation commands green, `./scripts/check.sh` green. T5+T6 checked; sprint `needs_validation`; next is P1. |
|| 2026-08-11 | S01 Validator (P1) | Validated and closed S01. Re-ran all sprint validation commands, ran `./scripts/check.sh`, and found/fixed two CI gaps so the harness tests and mypy run in CI. Merged `sprint/S01-benchmark-harness` into `main` (9d4ec3d). Closed GitHub issue #2. Updated ROADMAP/STATE/LEARNINGS. Next: S02 T0 — record the Linux + NVIDIA GPU host. |
|| 2026-08-11 | S02 executor (P0), T0 | Booted S02, created branch `sprint/S02-baseline-workloads` from `main`, read context budget (plan §20.2, §20.3-D, §29 Days 1-10, §2.4, §33.2-33.4). Cannot run `cobra-bench doctor --strict` on macOS (no GPU; strict mode requires GPU metadata per §33.2). Recorded blocker: need owner-provided Linux + NVIDIA GPU host access details. No code changes. |

## Notes for the next session

- S01 is merged to `main` and done.
- S02 is the active sprint (GPU required). T0 is the first task: run
  `cobra-bench doctor --strict` on the Linux GPU host and fill the Environment
  table. The owner has confirmed the host exists but details are still needed.
- The harness has zero Cobra-internal dependencies and measures arbitrary Python
  callables via manifest entrypoints.
- The plan's §36 approval record is pending; the S05 gate collects the
  formal sign-offs. Proceeding through M0 is explicitly authorized by the
  owner (2026-08-10).
- Autonomous Orca loop harness is present on `main` (`scripts/cobra_orca_loop.py`,
  wrapper, precheck).
- Security contact email remains a flagged placeholder in `SECURITY.md`.
