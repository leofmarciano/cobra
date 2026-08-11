# STATE — single source of truth

> Read me first. Update me last (every session). Keep me under ~80 lines:
> history belongs in sprint Session logs, not here.

**Last updated:** 2026-08-11 — S03 T1 complete (executor session)

## Now

| Field | Value |
|---|---|
| Milestone | M0 — Thesis validation |
| Active sprint | S03 — Disposable whole-program tracer (`orchestration/sprints/S03-disposable-tracer.md`) |
| Sprint status | `in_progress` |
| Current task | T2 — Dependency DAG builder |
| Branch | `sprint/S03-disposable-tracer` |
| Next action | Run P0 (Executor) to continue S03 with T2 |

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
| 2026-08-11 | S03 executor (P0), T1 complete | Added `experimental/tracer/` (`cobra-tracer` uv workspace member): torch recorder via real `TorchFunctionMode`, pandas recorder via method wrapping over plan §10.1 ops, numpy recorder via real `__array_function__` on a `TracedArray` subclass, opaque-node wrapper, and a `TraceSession`/`trace()` context manager tying them together with value-identity handles (tensor storage ptr / df object id / ndarray base id) and per-event metadata/timing. 19 tests pass (`uv run pytest experimental/tracer -q`); manually verified against the real `cobra_pipelines.model_ensemble.b0()` workload (510 events, both branches disjoint, overhead well under budget after fixing a `Path.resolve()`-per-frame hot-loop bug — see LEARNINGS.md). `./scripts/check.sh` passes. T1 checked off; sprint `in_progress`, next is T2. |
| 2026-08-11 | S02 validator (P1) | Independently reran `cobra-bench verify` (b0,b1), warm `run`, `analyze` for phase0; all passed. `./scripts/check.sh` passes (123 tests, no new warnings). Minor fixes: added missing `--output`/`--seed 42` to the sprint Validation block, and added D-008 to `DECISIONS.md` for the S02 dependency additions. Merged sprint branch to `main`; S02 status `done`. |
| 2026-08-11 | S02 executor (P0), T5 complete | Installed cudf-cu13 26.6.0 as real dependency; fixed `_engineer_features` cudf.pandas column-alignment issue. Ran `cobra-bench verify`, warm `run` (180 samples), and `analyze` for phase0. Captured Nsight Systems 2024.4.1 traces for all 6 workload×variant combos (WSL2 timestamp workaround applied) and wrote `docs/benchmarks/phase0-baseline.md` with absolute times, CIs, and bottleneck analysis. `./scripts/check.sh` passes (123 tests). T5 checked off; sprint `needs_validation`. |

## Notes for the next session

- S02 is merged to `main` and done; all tasks T0-T5 accepted.
- S03 is the active sprint (`sprint/S03-disposable-tracer`, branch exists).
  T1 (call-boundary recorder) is done — see `experimental/tracer/` and its
  README for the schema/usage. Next: T2 (dependency DAG builder) using the
  `input_handles`/`output_handles` already on every `Event`; then T3
  (critical path/parallelism reports) and T4 (findings memo). Next prompt
  is `P0-execute.md`.
- Baseline artifacts are on `main`:
  - `docs/benchmarks/phase0-baseline.md` — absolute times, CIs, bottleneck analysis.
  - `artifacts/raw/phase0/samples.jsonl` — 180 warm samples (30 per workload×variant).
  - `artifacts/analysis/phase0/{summary.md,summary.json,confidence_intervals.csv}`.
  - `artifacts/traces/phase0/*.nsys-rep` — Nsight Systems 2024.4.1 traces for all 6 combos.
- B1 is slightly slower than B0 on two of three workloads at this scale
  (parquet 0.897x, ensemble 0.944x, cv 1.041x), which is acceptable as the
  baseline Cobra must beat.
- The plan's §36 approval record is pending; the S05 gate collects the
  formal sign-offs. Proceeding through M0 is explicitly authorized by the
  owner (2026-08-10).
- Security contact email remains a flagged placeholder in `SECURITY.md`.
