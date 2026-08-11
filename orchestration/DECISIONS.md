# DECISIONS — loop-level decision ledger

Formal architecture decisions (ADRs) live in `docs/decisions/` once S00
creates them. This file is the lightweight ledger for **loop-level**
decisions: gate outcomes, roadmap changes, dependency additions, scope
calls. Gatekeeper sessions and the human write here; everyone reads it.

Format:

```
## D-NNN — <title>
- Date / by: YYYY-MM-DD / <human|gate session>
- Context: <1-2 lines>
- Decision: <1-2 lines>
- Consequences: <what changes downstream>
```

---

## D-001 — Orchestration model adopted

- Date / by: 2026-08-10 / owner (leofmarciano) + setup session
- Context: Cobra will be implemented 100% by AI executors with ~300k
  context, prone to losing state between sessions.
- Decision: File-based sprint loop (STATE/PROTOCOL/ROADMAP/sprints/prompts)
  with Executor/Validator role separation, WIP=1, and human-signed gates at
  day-30, day-90, and v0.1.
- Consequences: All sessions must follow `orchestration/PROTOCOL.md`.
  Filesystem + git are the only durable memory.

## D-002 — Setup-time owner choices

- Date / by: 2026-08-10 / owner
- Context: Setup questions before generating the sprint plan.
- Decision: (1) All artifacts in English. (2) Linux + NVIDIA GPU host is
  available from day one — GPU sprints are in the normal flow. (3) All
  sprints through v0.1 fully specified upfront; beta/v1 remain stubs until
  the S29 gate.
- Consequences: Gates may still invalidate later sprints; a `narrow`
  decision requires a Replanner pass over remaining sprint files.

## D-004 — Devin-only workers; harness spawns headless Devin CLI

- Date / by: 2026-08-11 / owner ("NAO USAREMOS CLAUDE! SOMENTE DEVIN") + review session
- Context: The original harness dispatched workers via `orca orchestration
  worker-start --agent claude`, but Orca's worker layer supports only
  claude/codex TUI agents and no managed Claude account exists. Owner
  mandates Devin for all agents.
- Decision: Workers are `devin --print` subprocesses spawned directly by
  `scripts/cobra_orca_loop.py` (blocking, one at a time — WIP=1 by
  construction). The Orca automation (provider devin) remains the hourly
  scheduler + supervisor that reports LOOP_RESULT lines to the operator.
  Default worker permission mode is `dangerous` (unattended runs need
  git/build/test without approval prompts); override via
  `--permission-mode` in the automation prompt if desired.
- Consequences: Requires one-time `devin auth login` on the host. Orca
  run/task/mailbox provenance is not used; progress classification is
  file-based (STATE.md + git), which the loop was designed around.

## D-006 — cobra-bench harness dependency: pyarrow

- Date / by: 2026-08-11 / S01 executor (P0), T4
- Context: S01 T4 requires Parquet output for raw sample records and analysis
  artifacts (plan §33.10: JSON-lines + Parquet; §33.8: analysis output).
- Decision: Added `pyarrow>=19.0,<20` as a runtime dependency of the
  `cobra-bench` workspace package (`benchmarks/harness/pyproject.toml`).
  Version 19.0.1 was published 2025-01-20 and is widely used in the Python
  data ecosystem.
- Consequences: `uv sync` installs pyarrow. Harness can now write/read
  `samples.parquet` alongside `samples.jsonl`.

## D-005 — cobra-bench harness dependencies: pyyaml, types-pyyaml

- Date / by: 2026-08-11 / S01 executor (P0), T1
- Context: S01 T1 requires a YAML manifest loader for `cobra_bench`
  (plan §33.1 explicitly lists `pyyaml` under captured `software:`
  versions, and the harness needs a YAML parser to implement it).
- Decision: Added `pyyaml>=6.0.3,<7` as a runtime dependency of the new
  `cobra-bench` workspace package (`benchmarks/harness/pyproject.toml`),
  and `types-pyyaml>=6.0,<7` as a root dev-group dependency for `mypy
  --strict` on `cobra_bench`. Both are long-published, widely used
  packages (PyYAML 6.0.3 already appears transitively via `pre-commit`/
  `deptry` in the existing lockfile).
- Consequences: `uv sync` now installs pyyaml/types-pyyaml. Future T4 will
  similarly need to add `pyarrow` (already named explicitly in the S01
  sprint file) — record that addition here when it lands.

## D-007 — Baseline pipeline package dependencies (torch, pandas, numpy, pyarrow)

- Date / by: 2026-08-11 / S02 executor (P0), T1
- Context: S02 T1 needs pandas, NumPy, PyArrow, and PyTorch for the
  `parquet_feature_inference` B0 baseline (plan §20.2, §20.3-D, §29).  The
  framework versions were pinned in S02-T0 (`support-matrix.yaml`) after
  verifying co-resolution with `cudf-cu13==26.6.0`.
- Decision: Added the pinned versions as runtime dependencies of the new
  `cobra-pipelines` workspace package (`benchmarks/pipelines/pyproject.toml`):
  `torch==2.13.0`, `numpy==2.4.6`, `pandas==2.3.3`, `pyarrow==23.0.1`.
  `cudf-cu13` is pinned but not yet added; it will be added when the B1
  variants (cudf.pandas) are wired in T4.
- Consequences: `uv sync` installs the four packages.  B0 workloads can now
  exercise the full Parquet → pandas → torch pipeline.  `cudf-cu13` will be
  added and the NVIDIA package index configured in T4.

## D-003 — Pending formal approvals (plan §36)

- Date / by: 2026-08-10 / setup session
- Context: Plan §36 requires sponsor sign-off on scope, semantic charter,
  B1 baseline, license, staffing, and stop conditions before
  implementation.
- Decision: Owner authorizes M0 to proceed now; the §36 sign-off checklist
  is collected at the S05 gate (semantic charter freeze) instead of before
  S00.
- Consequences: S05 cannot pass without the owner explicitly approving the
  §36 items (adapted to a solo-owner + AI team).
