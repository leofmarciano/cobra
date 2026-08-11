# LEARNINGS — append-only knowledge base

Rules: append at the top of the relevant section, never delete, never edit
old entries (strike through with `~~` if superseded and add a new entry).
Keep entries to 1-3 lines: symptom → cause → fix/rule. If an entry changes
how future sprints should work, ALSO flag it to the Validator so the sprint
files get updated via a Replanner session.

Format: `- [YYYY-MM-DD][S<NN>] lesson`

## Build & toolchain

- (none yet)

## Python / frameworks (torch, pandas, cuDF, Arrow)

- (none yet)

## CUDA / GPU host

- (none yet)

## MLIR / compiler core

- (none yet)

## Benchmarking & measurement

- (none yet)

## Loop & process

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
