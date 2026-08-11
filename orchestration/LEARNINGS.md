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

- [2026-08-10][setup] On this workstation, agent tooling refuses to write
  repo files whose NAME contains `trace-` (an editor/agent ignore pattern,
  not git — `git check-ignore` is clean). `tracer/` is fine. If a write is
  denied "matched by an ignore file", rename the file, don't fight it.
- [2026-08-10][setup] The technical plan is ~4,500 lines. Never read it in
  full; sprint files cite exact sections (§). Reading it whole wastes ~40k
  tokens of context.
