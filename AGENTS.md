# AGENTS.md — Read this first

This repository builds **Project Cobra** (an AI-native whole-program Python
compiler and heterogeneous parallel runtime) using an **AI-executed sprint
loop**. Every working session is performed by an AI agent with limited
context. This file is the entry point for every session.

## Mandatory boot sequence (in order, before doing anything else)

1. Read `orchestration/STATE.md` — the single source of truth for what is
   happening right now.
2. Read `orchestration/PROTOCOL.md` — the rules of the loop.
3. Read the **active sprint file** referenced by STATE.md
   (`orchestration/sprints/S<NN>-*.md`).
4. Read ONLY the sections of `COBRA_TECHNICAL_PLAN.md` listed in the active
   sprint's "Context budget". **Never read the full plan** — it is ~4,500
   lines and will waste your context.

## Hard rules (non-negotiable)

- **Scope**: Do only work defined in the active sprint. If you discover
  necessary work outside the sprint, write it down in the sprint's Session
  log and in `orchestration/STATE.md` under Blockers/Notes — do not do it.
- **WIP = 1**: Exactly one sprint is active at any time.
- **TDD**: No feature without a failing test first. See plan §18.
- **Wrong-code policy**: A compiler that is fast and wrong is defective.
  Silent wrong-code is release-blocking, always (plan §18.5).
- **Never weaken a test, tolerance, or assertion to make it pass.**
- **State discipline**: The LAST action of every session is updating
  `orchestration/STATE.md` and the sprint's Session log, then committing.
- **Ask the human** before: adding dependencies not named in the sprint,
  destructive operations, gate decisions, pushing to remote, or anything
  involving credentials/money.
- If reality and documents disagree (git says X, STATE says Y), stop and
  follow `orchestration/prompts/P2-recovery.md`.

## Document hierarchy

| Document | Role | Who writes it |
|---|---|---|
| `COBRA_TECHNICAL_PLAN.md` | Constitution. Architecture, gates, scope. | Human only |
| `orchestration/ROADMAP.md` | Sprint ledger and milestone map | Validator/Gatekeeper sessions |
| `orchestration/STATE.md` | What is true right now | Every session (last action) |
| `orchestration/sprints/*.md` | Work orders + session logs | Executor (checkboxes, log) |
| `orchestration/PROTOCOL.md` | Loop rules | Human only |
| `orchestration/LEARNINGS.md` | Append-only gotchas | Any session (append only) |
| `orchestration/DECISIONS.md` | Loop-level decision ledger | Gate sessions + human |

Conflicts resolve in this order: human instruction > DECISIONS.md >
TECHNICAL_PLAN > ROADMAP > sprint file > STATE.

## Environment note

## CI / CD

Every executor must leave the repo passing `./scripts/check.sh` before handoff.
CI on GitHub runs the same checks. Do not disable, weaken, or bypass a lint rule
unless the sprint explicitly permits it; if a rule blocks the active task,
record it as a blocker and ask the human.

The orchestration host may be macOS, but Cobra targets **Linux x86_64 +
NVIDIA CUDA**. All native (C++/CUDA) work must happen inside the dev
container or on the Linux GPU host recorded in STATE.md. Sprints are tagged
`CPU-only` or `NVIDIA GPU required`.
