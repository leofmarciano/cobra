# STATE — single source of truth

> Read me first. Update me last (every session). Keep me under ~80 lines:
> history belongs in sprint Session logs, not here.

**Last updated:** 2026-08-11 — S02 T0 done (doctor strict passes, framework versions pinned); starting T1

## Now

| Field | Value |
|---|---|
| Milestone | M0 — Thesis validation |
| Active sprint | S02 — Baseline workloads & B0/B1 report (`orchestration/sprints/S02-baseline-workloads.md`) |
| Sprint status | `in_progress` |
| Current task | T1 — Workload 1: `parquet_feature_inference` |
| Branch | `sprint/S02-baseline-workloads` |
| Next action | Run P0 (Executor) to implement T1 |

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
      compute cap 8.6, 10 GiB). CUDA toolkit presence verified by T0 (see
      below): no system-wide `nvcc` is installed, but pip wheels
      (`nvidia-cuda-nvcc-cu13` etc.) provide everything needed.

## Environment

| Item | Value |
|---|---|
| Orchestration host | WSL2 Ubuntu 24.04.1 LTS (this session) — native builds allowed; GPU available |
| Dev/bench host | WSL2 Ubuntu 24.04.1 LTS / kernel 6.6.87.2-microsoft-standard-WSL2 / Intel Core i9-10900F (12 vCPU) / 15.62 GiB RAM |
| GPU availability | NVIDIA GeForce RTX 3080, 10 GiB, driver 591.86, compute cap 8.6 (sm_86); `nvidia-smi` reports max supported CUDA 13.1. System-wide `nvcc` is absent — not required; CUDA 13 toolkit pieces are pulled in as pip wheel deps (`nvidia-cuda-nvcc-cu13`, `nvidia-cuda-runtime-cu13`, ...) |
| `cobra-bench doctor --strict` | PASSES on this host as of 2026-08-11; report committed at `artifacts/environment/primary-host.json` |
| Framework version pins (S02-T0) | torch 2.13.0, numpy 2.4.6, pandas 2.3.3, pyarrow 23.0.1, cudf-cu13 26.6.0 — see `support-matrix.yaml` for rationale (cudf-cu13 26.6.0 caps numpy <2.5 and pandas <2.4; verified co-resolvable via `uv pip install --dry-run`) |
| Python toolchain | `uv` (to be pinned in S00); harness venv runs Python 3.13.12 |
| Remote | github.com/leofmarciano/cobra (do NOT push without human ask) |
| Worker agent | Devin CLI headless (`devin -p`), spawned by `scripts/cobra_orca_loop.py`; default `--permission-mode dangerous` (owner-approved for unattended runs, D-004) |

## Last 3 sessions

| Date | Session | Result |
|---|---|---|
| 2026-08-11 | S02 executor (P0), T0 complete | Ran `cobra-bench doctor --strict` on the WSL2 + RTX 3080 host — passes; committed `artifacts/environment/primary-host.json`. Researched and pinned framework versions in `support-matrix.yaml` (torch 2.13.0, numpy 2.4.6, pandas 2.3.3, pyarrow 23.0.1, cudf-cu13 26.6.0), verifying co-resolution with `uv pip install --dry-run` in a scratch venv (no packages installed into the repo env). Discovered cudf-cu13 26.6.0 caps numpy<2.5/pandas<2.4/pyarrow<24, so pinned versions are the newest releases under those ceilings rather than the newest upstream releases. Updated STATE.md Environment table. T0 checked off; next is T1 (`parquet_feature_inference` workload). |
| 2026-08-11 | S02 executor (P0), T0 blocked | Booted and read context budget. GPU host now available (WSL2 + RTX 3080), but repo state contradicts itself: working tree on `main` while `STATE.md` declares branch `sprint/S02-baseline-workloads`; git history shows S02 branch already merged via PR #32 (`995e564`); `ROADMAP.md` ledger lists S02 as `not_started` while `STATE.md` lists `in_progress`. Per `AGENTS.md`/`P0-execute.md`, stopping for `P2-recovery.md`. |
| 2026-08-11 | S01 Validator (P1) | Validated and closed S01. Re-ran all sprint validation commands, ran `./scripts/check.sh`, and found/fixed two CI gaps so the harness tests and mypy run in CI. Merged `sprint/S01-benchmark-harness` into `main` (9d4ec3d). Closed GitHub issue #2. Updated ROADMAP/STATE/LEARNINGS. Next: S02 T0 — record the Linux + NVIDIA GPU host. |

## Notes for the next session

- S01 is merged to `main` and done.
- S02 T0 is done: GPU host recorded, `doctor --strict` passes, framework
  versions pinned in `support-matrix.yaml`. Packages are NOT yet installed
  into the repo's `uv` environment — T1-T4 will need to add them as real
  dependencies (torch, numpy, pandas, pyarrow, cudf-cu13) per the pins
  above; record any new dependency add in the sprint log + DECISIONS.md.
- GPU host: WSL2 + RTX 3080 (driver 591.86, compute cap 8.6, 10 GiB, CUDA
  13.1 max per driver). No system `nvcc`; pip wheels supply CUDA 13
  toolkit components.
- The harness has zero Cobra-internal dependencies and measures arbitrary Python
  callables via manifest entrypoints.
- The plan's §36 approval record is pending; the S05 gate collects the
  formal sign-offs. Proceeding through M0 is explicitly authorized by the
  owner (2026-08-10).
- Autonomous Orca loop harness is present on `main` (`scripts/cobra_orca_loop.py`,
  wrapper, precheck).
- Security contact email remains a flagged placeholder in `SECURITY.md`.
