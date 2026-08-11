# STATE — single source of truth

> Read me first. Update me last (every session). Keep me under ~80 lines:
> history belongs in sprint Session logs, not here.

**Last updated:** 2026-08-11 — S01 validated and merged; S02 is next

## Now

|| Field | Value |
|---|---|---|
|| Milestone | M0 — Thesis validation |
|| Active sprint | S02 — Baseline workloads & B0/B1 report (`orchestration/sprints/S02-baseline-workloads.md`) |
|| Sprint status | `not_started` |
|| Current task | T0 — Record the GPU host |
|| Branch | `sprint/S02-baseline-workloads` |
|| Next action | Run `orchestration/prompts/P0-execute.md` in a fresh session |

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

|| Item | Value |
|---|---|---|
|| Orchestration host | macOS (owner laptop) — docs/git only, no native builds |
|| Dev/bench host | **TBD** — first GPU sprint must record: OS, kernel, CPU, RAM, GPU, driver, CUDA toolkit |
|| GPU availability | Confirmed available by owner (2026-08-10) |
|| Python toolchain | `uv` (to be pinned in S00) |
|| Remote | github.com/leofmarciano/cobra (do NOT push without human ask) |
|| Worker agent | Devin CLI headless (`devin -p`), spawned by `scripts/cobra_orca_loop.py`; default `--permission-mode dangerous` (owner-approved for unattended runs, D-004) |

## Last 3 sessions

|| Date | Session | Result |
|---|---|---|---|
|| 2026-08-11 | S01 executor (P0), T4 | Implemented `cobra_bench.results` (§33.10 schema, JSON-lines + Parquet IO), `cobra_bench.stats` (median/p95/p99/geomean/CV, bootstrap-95% CI, speedup significance when CI excludes 1.0x), `cobra_bench.analyze`, and the `cobra-bench` CLI entry point with the `analyze` subcommand. Added `pyarrow>=19.0,<20` (D-006) and harness-local mypy overrides for pyarrow. 30 new TDD tests; `uv run pytest benchmarks/harness -q` (86 passed), `mypy --strict` clean, ruff clean, `./scripts/check.sh` green. T4 checked; sprint `in_progress`; next is T5. |
|| 2026-08-11 | S01 executor (P0), T5+T6 | Implemented full `cobra-bench` CLI (`doctor`, `verify`, `run`, `analyze`, `compare`), `cobra_bench.runner` (entrypoint resolution, oracle factory, warm timing, cold subprocess placeholder, sample recording), `cobra_bench.compare` (threshold check between `summary.json` files), and `cobra_bench.guardrails` (mixed-phase refusal, input-fingerprint consistency, <30 sample warning, `--no-oracle` opt-out with loud warning). Extended manifest/stats for input fingerprints and phase. 34 new TDD tests; `uv run pytest benchmarks/harness -q` (120 passed), `mypy --strict` clean, ruff clean, sprint validation commands green, `./scripts/check.sh` green. T5+T6 checked; sprint `needs_validation`; next is P1. |
|| 2026-08-11 | S01 Validator (P1) | Validated and closed S01. Re-ran all sprint validation commands, ran `./scripts/check.sh`, and found/fixed two CI gaps so the harness tests and mypy run in CI. Merged `sprint/S01-benchmark-harness` into `main` (9d4ec3d). Closed GitHub issue #2. Updated ROADMAP/STATE/LEARNINGS. Next: S02 T0 — record the Linux + NVIDIA GPU host. |

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
