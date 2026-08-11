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
