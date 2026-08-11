# STATE — single source of truth

> Read me first. Update me last (every session). Keep me under ~80 lines:
> history belongs in sprint Session logs, not here.

**Last updated:** 2026-08-11 — S03 PR #45 review/CI follow-up 3 in progress (executor session)

## Now

| Field | Value |
|---|---|
| Milestone | M0 — Thesis validation |
| Active sprint | S03 — Disposable whole-program tracer (`orchestration/sprints/S03-disposable-tracer.md`) |
| Sprint status | `needs_validation` |
| Current task | Push review follow-up 3; monitor CI, CodeQL, and Devin approval |
| Branch | `sprint/S03-disposable-tracer` |
| Next action | Push the validated review batch and monitor all PR checks/review threads |

## Blockers

- GitHub CodeQL upload is disabled because this private repository reports no
  `security_and_analysis` setting; enabling it is an owner-controlled gate.
  The workflow keeps analysis source-backed and documents the required
  `upload: true` follow-up.

## Human-input queue

Items an executor needs from the owner; answer by editing this list.

- [x] ~~Run `devin auth login`~~ — resolved 2026-08-11: owner confirmed the
      Orca automation environment authenticates fine; the "Not logged in"
      was an artifact of a sandboxed review shell only. Not a blocker.
- [ ] Security contact email for `SECURITY.md` (needed in S00-T1)
- [ ] Enable Advanced Security for `leofmarciano/cobra`; then set
      `.github/workflows/security.yml` to `upload: true` and rerun Security.
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
| Remote | github.com/leofmarciano/cobra (PR #45 push authorized by owner on 2026-08-11) |
| Worker agent | Devin CLI headless (`devin -p`), spawned by `scripts/cobra_orca_loop.py`; default `--permission-mode dangerous` (owner-approved for unattended runs, D-004) |

## Last 3 sessions

| Date | Session | Result |
|---|---|---|
| 2026-08-11 | S03 executor (PR #45 review follow-up) | Fixed the first review/CI batch and regenerated tracer evidence. `./scripts/check.sh --ci`, 41 tracer tests, and 17 pipeline tests passed. |
| 2026-08-11 | S03 executor (PR #45 review follow-up 2) | Added the persistent cuDF worker/cache, pandas boundaries, generation-aware handles, tolerance propagation, memoized reachability, and source-backed CodeQL language detection. `./scripts/check.sh --ci` and 44 tracer tests passed; CodeQL upload remains owner-controlled. |
| 2026-08-11 | S03 executor (PR #45 review follow-up 3) | Added package CI coverage/Linux markers, ndarray lineage, mutation-aware/frontier-fenced DAG edges, secure worker I/O, and fresh benchmark/tracer evidence. `./scripts/check.sh --ci`, 48 tracer tests, and 187 tests with 9 GPU cases deselected pass. |

## Notes for the next session

- S03 tasks T1–T4 are complete, but PR #45 review follow-up remains open until
  the CodeQL upload gate is enabled and Devin approves the final head. Branch
  `sprint/S03-disposable-tracer` contains the corrected reports, findings memo,
  fresh raw samples, and review/CI fixes.
- Next prompt is `P1-validate.md`: an independent Validator session must
  verify the work, run `./scripts/check.sh`, and either close the sprint or
  reopen with blockers.
- S04 will implement the three §29 high-risk experiments against the
  opportunities identified in `docs/benchmarks/phase0-tracer-findings.md`.
- S02 is merged to `main` and done; all tasks T0-T5 accepted.
- Baseline artifacts are on `main`:
  - `docs/benchmarks/phase0-baseline.md` — absolute times, CIs, bottleneck analysis.
  - `artifacts/raw/phase0/samples.jsonl` — 180 warm samples (30 per workload×variant).
  - `artifacts/analysis/phase0/{summary.md,summary.json,confidence_intervals.csv}`.
  - `artifacts/traces/phase0/*.nsys-rep` — Nsight Systems 2024.4.1 traces for all 6 combos.
- The plan's §36 approval record is pending; the S05 gate collects the
  formal sign-offs. Proceeding through M0 is explicitly authorized by the
  owner (2026-08-10).
- Security contact email remains a flagged placeholder in `SECURITY.md`.
