# LEARNINGS — append-only knowledge base

Rules: append at the top of the relevant section, never delete, never edit
old entries (strike through with `~~` if superseded and add a new entry).
Keep entries to 1-3 lines: symptom → cause → fix/rule. If an entry changes
how future sprints should work, ALSO flag it to the Validator so the sprint
files get updated via a Replanner session.

Format: `- [YYYY-MM-DD][S<NN>] lesson`

## Build & toolchain

- [2026-08-11][S01 validation] Adding a new workspace package with tests
  requires updating `scripts/ci/python-test.sh` and `python-lint.sh`. Validator
  found `./scripts/check.sh` was not running `benchmarks/harness` tests or mypy
  on the harness; fixed by adding the package paths to those scripts.
- [2026-08-11][S02] A dedicated `cobra-pipelines` workspace package keeps the
  heavy framework dependencies (torch, pandas, pyarrow) out of `cobra-bench`
  itself while still making workload entrypoints importable via `uv sync`.
- [2026-08-11][S02] `npx knip` on Node 24 may install a newer `knip` (6.x)
  than the package-lock pinned version (5.x).  If `knip` reports unused
  dependencies for packages that are only referenced in `package.json`
  scripts and whose binaries are in `ignoreBinaries`, add them to
  `ignoreDependencies` or pin the `npx` version to the lockfile version.

## Python / frameworks (torch, pandas, cuDF, Arrow)

- [2026-08-11][S02] `cudf-cu13==26.6.0` (RAPIDS wheel for CUDA 13 drivers)
  constrains `numpy<2.5,>=1.26`, `pandas<2.4.0,>=2.0`, `pyarrow<24,>=19.0.0`.
  The current upstream-latest releases (numpy 2.5.x, pandas 3.0.x, pyarrow
  25.x) are NOT installable alongside cudf.pandas. When pinning "latest
  stable" framework versions for a B1 baseline that uses `cudf.pandas`,
  resolve the whole set together (e.g. `uv pip install --dry-run`) rather
  than picking each package's latest release independently.
- [2026-08-11][S02] No system-wide `nvcc`/CUDA toolkit is required to run
  torch/cudf GPU workloads via pip wheels — `nvidia-cuda-nvcc-cu13`,
  `nvidia-cuda-runtime-cu13`, etc. ship as transitive pip deps of the
  cu13-tagged wheels and are sufficient for pip-wheel-based (non-native-build)
  workloads.

## CUDA / GPU host

- [2026-08-11][S02] `torch.compile` with the Inductor backend calls
  `nvcc --version` during repro/debug graph serialization. If `nvcc` is not
  on PATH (pip-wheel install puts it under `site-packages/nvidia/cu13/bin/`),
  the compilation fails with a misleading `PermissionError: [Errno 13]
  Permission denied: 'nvcc'`. Fix: ensure the pip-wheel nvcc dir is on PATH
  before calling `torch.compile`. The `_compile_env.ensure_nvcc_in_path()`
  helper in `cobra_pipelines` handles this.

## MLIR / compiler core

- (none yet)

## Benchmarking & measurement

- [2026-08-11][S02] When comparing B0 vs B1 outputs, `torch.compile` may
  reorder float32 ops and introduce up to ~1e-3 absolute differences in
  softmax/confidence outputs.  The harness `_float_key` treats Python `float`
  as `"float64"` by default (rtol=1e-5), which is too strict for float32
  model outputs serialized as Python floats.  Fix: add a `"float"` key to
  `rtol_by_dtype`/`atol_by_dtype` in the suite YAML (e.g., `float: 1e-3`)
  so the harness applies float32-appropriate tolerance.
- [2026-08-11][S02] The `approx` correctness comparator should inspect the
  concrete scalar type name (`float`, `float32`, `float64`) to pick a tolerance
  from `rtol_by_dtype` / `atol_by_dtype`, and it must handle `None`, `bool`,
  `str`, nested `dict`/`list`, and numeric tolerance with `math.isclose`
  (plan §33.4).

- [2026-08-11][S01 validation] The timing engine's `stability_window`
  currently doubles as the earliest point at which warmup can stop; there is no
  separate `min_warmup` count. If future sprints need stricter warmup control,
  add `min_warmup` to `TimingConfig` and require it before `_is_stable`.
- [2026-08-11][S01 validation] The cold runner uses `random.shuffle` and
  ignores `--seed`; if S02 needs reproducible cold-path ordering, switch to a
  `random.Random(options.seed)` instance.
- [2026-08-11][S01] When hand-writing benchmark manifest/suite YAML,
  quote any all-digit string field (commit SHAs, hashes) explicitly
  (`commit: "0000...0"`), otherwise PyYAML's default loader parses it as
  an `int` and schema validation rejects it as the wrong type.
- [2026-08-11][S01] A hand-rolled dict-pop validator must still `pop()`
  the key even when short-circuiting because the value is `None`/absent —
  otherwise a later "reject unknown keys" pass reports a false-positive
  "unknown field" for legitimately-null optional fields.

## Loop & process

- [2026-08-11][S01 recovery] A session that completes a task and begins the next
  one can leave the working tree staged but uncommitted, and `STATE.md` one task
  behind. Recovery found T2 committed but no STATE handoff and T3 fully staged
  but uncommitted. Combined with an unrelated, half-finished
  `scripts/cobra_orca_loop.py` edit, this blocked `./scripts/check.sh`. Fix/rule:
  a handoff must end with a clean `git status` (all changes committed), and
  non-sprint/tooling changes must be on their own branch, never mixed with a
  sprint task.
- [2026-08-11][S00 validation] Legal or canonical text copied from a URL (e.g.,
  `LICENSE`) must be verified with `diff -u` against the fetched source, not just
  by inspection. A `LICENSE` passed all lint/tests but was missing ~50 lines of
  the LLVM canonical text. Validator checklist: always diff canonical legal
  documents on the first sprint that introduces them.
- [2026-08-11][S00 recovery] RECURRED (2nd time same day): a P0 session
  reopened for a narrow, single-task fix (T1: repair `LICENSE`) instead
  produced unrelated, uncommitted CI/npm tooling (GH workflows, biome/knip,
  pre-commit, package.json) and never touched `LICENSE`. Hypothesis: when
  "Current task" in STATE.md is a small legal-text fix, the executor prompt
  may default to broader "repo hygiene" scope instead. Fix/rule: P0 sessions
  MUST re-read the sprint file's exact task bullet before acting, touch only
  files needed for that bullet's Accept criteria, and commit immediately
  after — never leave a session boundary with uncommitted changes, no matter
  how small the remaining diff feels. Flagged for Replanner: consider making
  P0-execute.md require quoting the current task's Do/Accept text back
  before any file writes.
- [2026-08-11][S00 recovery] A session that does not commit its work leaves the
  next session in an unrecoverable state. In this case an unfinished session had
  uncommitted CI/npm tooling WIP on top of a44e1e0. S00 validation still passed
  on the last commit, so the WIP was rescued to `rescue/S00-2026-08-11` and the
  sprint branch reset. While rescuing, `scripts/cobra_orca_loop.py` was being
  mutated in the background (likely an IDE/linter), requiring an amended rescue
  commit. Rescue and reset quickly; do not try to validate a moving target.
- [2026-08-11][review] Orca `orchestration worker-start --agent` accepts only
  claude/codex — Devin workers must be spawned as `devin -p` subprocesses.
- [2026-08-11][review] ~~Headless `devin -p` fails with "Not logged in"
  until `devin auth login`.~~ Superseded same day: credentials exist and the
  Orca automation environment authenticates fine (owner-verified). The
  failure only reproduces inside IDE-sandboxed agent shells, which cannot
  read `~/.local/share/devin/credentials.toml`. Do NOT treat sandboxed-shell
  auth checks as evidence about the automation environment.
- [2026-08-11][review] Orca `orchestration check --wait` REPLAYS the same
  unacknowledged batch until `--ack <delivery_id>` — polling without ack
  reads stale worker_done messages forever. (Moot now, but recorded.)
- [2026-08-11][review] macOS has no `timeout` binary; use Python subprocess
  timeouts or `gtimeout` (coreutils).
- [2026-08-10][setup] On this workstation, agent tooling refuses to write
  repo files whose NAME contains `trace-` (an editor/agent ignore pattern,
  not git — `git check-ignore` is clean). `tracer/` is fine. If a write is
  denied "matched by an ignore file", rename the file, don't fight it.
- [2026-08-10][setup] The technical plan is ~4,500 lines. Never read it in
  full; sprint files cite exact sections (§). Reading it whole wastes ~40k
  tokens of context.
- [2026-08-11][S00] Background subagents can edit shared state files
  (`STATE.md`, sprint file) and leave unrelated working-tree changes.
  Re-verify `git status` after a subagent returns; revert or scope commits
  before the Executor handoff.
- [2026-08-11][S00] `uvx --from yamllint yamllint` warnings for missing
  document start (`---`) and YAML 1.1 truthy keys (`on:`) are easy to fix;
  quote truthy keys and add `---` to keep the workflow YAML clean.
