# STATE — single source of truth

> Read me first. Update me last (every session). Keep me under ~80 lines:
> history belongs in sprint Session logs, not here.

**Last updated:** 2026-08-11 — S01 T1 done (package + manifest schema)

## Now

| Field | Value |
|---|---|
| Milestone | M0 — Thesis validation |
| Active sprint | S01 — Benchmark harness (cobra-bench v0) (`orchestration/sprints/S01-benchmark-harness.md`) |
| Sprint status | `in_progress` |
| Current task | T2 — Machine metadata collector (`cobra-bench doctor`) |
| Branch | `sprint/S01-benchmark-harness` |
| Next action | Run `orchestration/prompts/P0-execute.md` in a fresh session |

## Blockers

- (none)

## Human-input queue

Items an executor needs from the owner; answer by editing this list.

- [x] ~~Run `devin auth login`~~ — resolved 2026-08-11: owner confirmed the
      Orca automation environment authenticates fine; the "Not logged in"
      was an artifact of a sandboxed review shell only. Not a blocker.
- [ ] Security contact email for `SECURITY.md` (needed in S00-T1)
- [ ] Linux + NVIDIA GPU host details (hostname/access, GPU model, driver,
      CUDA toolkit) — needed no later than S02. Owner confirmed hardware
      exists (2026-08-10).

## Environment

| Item | Value |
|---|---|
| Orchestration host | macOS (owner laptop) — docs/git only, no native builds |
| Dev/bench host | **TBD** — first GPU sprint must record: OS, kernel, CPU, RAM, GPU, driver, CUDA toolkit |
| GPU availability | Confirmed available by owner (2026-08-10) |
| Python toolchain | `uv` (to be pinned in S00) |
| Remote | github.com/leofmarciano/cobra (do NOT push without human ask) |
| Worker agent | Devin CLI headless (`devin -p`), spawned by `scripts/cobra_orca_loop.py`; default `--permission-mode dangerous` (owner-approved for unattended runs, D-004) |

## Last 3 sessions

| Date | Session | Result |
|---|---|---|
| 2026-08-11 | S00 executor (P0) | Repaired `LICENSE` to match https://llvm.org/LICENSE.txt verbatim (only project-name header changed to "The Cobra Project"). `diff -u` against the canonical file shows exactly one line. All S00 validation commands pass (`uv sync`, `./scripts/check.sh`, 80 READMEs, import smoke). Sprint status set to `needs_validation`; next is P1. |
| 2026-08-11 | S00 validation (P1) | All S00 validation commands pass from a clean checkout. Acceptance audit confirms: LICENSE is verbatim canonical (one-line project-name substitution); all six governance docs exist; repository skeleton matches plan §16.1; packaging imports as `cobra_compiler` with version `0.0.1.dev0`; ADR template + ADR-0001..0005 present; lint CI and local check script green; no anti-gaming findings. Sprint merged into `main`; S01 started. |
| 2026-08-11 | S01 executor (P0), T1 | Created `benchmarks/harness/` as a `uv` workspace member package `cobra-bench` and implemented the §33.1 manifest as typed dataclasses + a field-level-error YAML loader (`cobra_bench.manifest`), with strict-mode rejection of `manual: true` sections. Added `benchmarks/suites/example.yaml` + 11 TDD unit tests, all green; `mypy --strict` clean; `./scripts/check.sh` green. Added `pyyaml`/`types-pyyaml` deps (D-005). T1 checked; sprint `in_progress`; next is T2 (`cobra-bench doctor`). |

## Notes for the next session

- S01 is the active sprint, `in_progress`, T1 done: run
  `orchestration/prompts/P0-execute.md` in a fresh session on branch
  `sprint/S01-benchmark-harness`, starting at T2 (`cobra-bench doctor`).
- S00 is merged to `main` and done.
- `cobra-bench` package lives at `benchmarks/harness/` (src layout, uv
  workspace member); manifest schema is `cobra_bench.manifest`; the T1
  session log has full detail.
- The plan's §36 approval record is pending; the S05 gate collects the
  formal sign-offs. Proceeding through M0 is explicitly authorized by the
  owner (2026-08-10).
- Autonomous Orca loop harness is present on `main` (`scripts/cobra_orca_loop.py`,
  wrapper, precheck).
- Security contact email remains a flagged placeholder in `SECURITY.md`.
- Linux + NVIDIA GPU host details still need to be recorded before S02.
