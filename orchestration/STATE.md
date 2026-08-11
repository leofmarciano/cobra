# STATE — single source of truth

> Read me first. Update me last (every session). Keep me under ~80 lines:
> history belongs in sprint Session logs, not here.

**Last updated:** 2026-08-11 — S01 T3 done; T4 next (recovered from uncommitted WIP)

## Now

| Field | Value |
|---|---|
| Milestone | M0 — Thesis validation |
| Active sprint | S01 — Benchmark harness (cobra-bench v0) (`orchestration/sprints/S01-benchmark-harness.md`) |
| Sprint status | `in_progress` |
| Current task | T4 — Result schema + statistics (`cobra-bench analyze`) |
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
| 2026-08-11 | S01 executor (P0), T1 | Created `benchmarks/harness/` as a `uv` workspace member package `cobra-bench` and implemented the §33.1 manifest as typed dataclasses + a field-level-error YAML loader (`cobra_bench.manifest`), with strict-mode rejection of `manual: true` sections. Added `benchmarks/suites/example.yaml` + 11 TDD unit tests, all green; `mypy --strict` clean; `./scripts/check.sh` green. Added `pyyaml`/`types-pyyaml` deps (D-005). T1 checked; sprint `in_progress`; next is T2 (`cobra-bench doctor`). |
| 2026-08-11 | S01 executor (P0), T2 | Implemented `cobra_bench.doctor`: OS/kernel/CPU/NUMA/RAM collectors, GPU metadata via `nvidia-smi` (with mocked fakes for CI), software versions via `importlib.metadata`, strict-mode validation, and JSON output to `artifacts/environment.json`. 27 TDD unit tests, all green; `mypy --strict` clean; `./scripts/check.sh` green. Committed as `S01 T2: machine metadata collector (cobra-bench doctor)`. Handoff was not recorded before the session ended. |
| 2026-08-11 | S01 recovery (P2) | Found the sprint branch with T1 and T2 committed but T2 handoff missing; T3 was fully staged but uncommitted. Verified T3 (56 tests pass, mypy/ruff clean), committed it as `S01: recovered work-in-progress (T3 timing protocol engine)`, rescued an unrelated broken orca-loop lock WIP to `rescue/S01-2026-08-11`, reverted `scripts/cobra_orca_loop.py` on the sprint branch, and removed `scripts/.cobra_loop.lock`. Working tree clean; `./scripts/check.sh` green. STATE.md updated to current task T4. |

## Notes for the next session

- S01 is the active sprint, `in_progress`, T1-T3 done: run
  `orchestration/prompts/P0-execute.md` in a fresh session on branch
  `sprint/S01-benchmark-harness`, starting at T4 (result schema + statistics).
- S00 is merged to `main` and done.
- `cobra-bench` package lives at `benchmarks/harness/` (src layout, uv
  workspace member); manifest schema is `cobra_bench.manifest`; timing
  protocol is `cobra_bench.timing`; the sprint Session logs have full detail.
- The plan's §36 approval record is pending; the S05 gate collects the
  formal sign-offs. Proceeding through M0 is explicitly authorized by the
  owner (2026-08-10).
- Autonomous Orca loop harness is present on `main` (`scripts/cobra_orca_loop.py`,
  wrapper, precheck).
- Security contact email remains a flagged placeholder in `SECURITY.md`.
- Linux + NVIDIA GPU host details still need to be recorded before S02.
