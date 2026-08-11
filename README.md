# Cobra

An AI-native whole-program Python compiler and heterogeneous parallel
runtime: capture ordinary Python AI pipelines (pandas + PyTorch + glue),
prove safe dependencies, and automatically choose parallel execution,
device placement, memory movement, CUDA Graphs, vendor libraries, and
generated kernels — with eager fallback whenever optimization is unsafe
or unprofitable.

**Status:** pre-implementation. The technical constitution is
[`COBRA_TECHNICAL_PLAN.md`](COBRA_TECHNICAL_PLAN.md); execution is
organized as an AI-driven sprint loop under [`orchestration/`](orchestration/).

## How this project is built

Cobra is implemented 100% by AI executor sessions coordinated through a
file-based loop (models have limited context; the repo + git history are
the durable memory):

```
orchestration/
├── STATE.md        ← what is true right now (read first, updated last)
├── ROADMAP.md      ← 30 sprints to v0.1, milestones M0-M4, 3 human gates
├── PROTOCOL.md     ← rules: session lifecycle, WIP=1, TDD, validation
├── LEARNINGS.md    ← append-only gotchas
├── DECISIONS.md    ← gate outcomes and loop-level decisions
├── prompts/        ← paste-ready prompts (P0 execute … P4 replan)
└── sprints/        ← S00…S29 work orders + session logs
```

## Operating the loop (human)

1. **Execute:** open a fresh AI session in this repo, paste
   `orchestration/prompts/P0-execute.md`. The agent reads STATE, works
   the active sprint, commits, and hands off.
2. **Validate:** when STATE says `needs_validation`, paste
   `orchestration/prompts/P1-validate.md` into a NEW session. It
   adversarially verifies and closes (or reopens) the sprint.
3. **Gates:** at S05 / S21 / S29, paste
   `orchestration/prompts/P3-gate-review.md`; the agent assembles
   evidence, you decide go / narrow / stop.
4. Lost/confused state → `orchestration/prompts/P2-recovery.md`.
   Roadmap changes → `orchestration/prompts/P4-replan.md`.

Milestones: **M0** thesis validation (benchmarks first, day-30 kill
gate) → **M1** compiler skeleton (MLIR dialects, capture, guards,
fallback) → **M2** native runtime + CUDA scheduler → **M3** framework
adapters + day-90 evidence → **M4** hardening + v0.1 gates (§24.2).

Targets Linux x86_64 + NVIDIA CUDA. License: Apache-2.0 WITH
LLVM-exception (created in S00).
