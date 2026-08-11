# STATE — single source of truth

> Read me first. Update me last (every session). Keep me under ~80 lines:
> history belongs in sprint Session logs, not here.

**Last updated:** 2026-08-11 — S02 T5 done; all tasks complete, awaiting validation

## Now

| Field | Value |
|---|---|
| Milestone | M0 — Thesis validation |
| Active sprint | S02 — Baseline workloads & B0/B1 report (`orchestration/sprints/S02-baseline-workloads.md`) |
| Sprint status | `needs_validation` |
| Current task | T5 — Baseline measurement + profiler evidence (complete) |
| Branch | `sprint/S02-baseline-workloads` |
| Next action | Run P1 (Validator) to close S02 |

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
| 2026-08-11 | S02 executor (P0), T5 complete | Installed cudf-cu13 26.6.0 as real dependency; fixed `_engineer_features` cudf.pandas column-alignment issue. Ran `cobra-bench verify`, warm `run` (180 samples), and `analyze` for phase0. Captured Nsight Systems 2024.4.1 traces for all 6 workload×variant combos (WSL2 timestamp workaround applied) and wrote `docs/benchmarks/phase0-baseline.md` with absolute times, CIs, and bottleneck analysis. `./scripts/check.sh` passes (123 tests). T5 checked off; sprint `needs_validation`. |
| 2026-08-11 | S02 executor (P0), T4 complete | Implemented B1 variants for all 3 workloads: `torch.compile(mode=default)` on models + `cudf.pandas` where applicable. Added `_compile_env.py` for pip-wheel nvcc PATH setup, `nvidia-cuda-nvcc==13.0.88` dep. Extended harness `_float_key` for `"float"` tolerance key. All 6 workload×variant combos pass `cobra-bench verify`; `./scripts/check.sh` passes (123 tests). T4 checked off; next is T5. |
| 2026-08-11 | S02 executor (P0), T2+T3 complete | Implemented `model_ensemble` b0 (MLP + TransformerEncoder, weighted aggregation; independence proven in test) and `cv_preprocess_inference_postprocess` b0 (resnet18 with CPU preprocessing; torchvision==0.28.0 added). All 3 workloads pass `cobra-bench verify`; `./scripts/check.sh` passes. T2+T3 checked off; next is T4 (B0/B1 variants). |

## Notes for the next session

- S01 is merged to `main` and done.
- S02 is complete; all tasks T0-T5 are checked off. Sprint status is
  `needs_validation`; next prompt is `P1-validate.md`.
- Baseline artifacts are committed on `sprint/S02-baseline-workloads`:
  - `docs/benchmarks/phase0-baseline.md` — absolute times, CIs, bottleneck analysis.
  - `artifacts/raw/phase0/samples.jsonl` — 180 warm samples (30 per workload×variant).
  - `artifacts/analysis/phase0/{summary.md,summary.json,confidence_intervals.csv}`.
  - `artifacts/traces/phase0/*.nsys-rep` — Nsight Systems 2024.4.1 traces for all 6 combos.
  - `artifacts/traces/phase0/summaries/*.csv` — exported `cuda_gpu_kern_sum`, `cuda_api_sum`, `osrt_sum`.
- `cudf-cu13==26.6.0` is now a real dependency in
  `benchmarks/pipelines/pyproject.toml`; a small NumPy-normalization fix in
  `_engineer_features` makes the Parquet workload robust under cudf.pandas.
- B1 is slightly slower than B0 on two of three workloads at this scale
  (parquet 0.897x, ensemble 0.944x, cv 1.041x), which is acceptable as the
  baseline Cobra must beat.
- The plan's §36 approval record is pending; the S05 gate collects the
  formal sign-offs. Proceeding through M0 is explicitly authorized by the
  owner (2026-08-10).
- Autonomous Orca loop harness is present on `main` (`scripts/cobra_orca_loop.py`,
  wrapper, precheck).
- Security contact email remains a flagged placeholder in `SECURITY.md`.
