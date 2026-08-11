# ROADMAP — milestones, sprint ledger, gates

Scope of this roadmap: **through v0.1 developer preview** (fully detailed).
Beta and v1 exist as stubs in `sprints/POST-V01-ROADMAP.md` and are expanded
via `prompts/P4-replan.md` only after the S29 gate.

Mapping to the technical plan: M0 = Phase 0 / 90-day plan days 1-30.
M1 ≈ days 31-60 (Phase 1 + start of Phase 2). M2 = days 61-75. M3 = days
76-90. M4 completes Phases 2-3 to hit the §24.2 v0.1 gates.

## Rules

- **WIP = 1.** Sprints execute in ledger order unless a recorded decision
  (DECISIONS.md) reorders them.
- Status values: `not_started | in_progress | needs_validation | blocked |
  done | skipped`. Only Validator/Gatekeeper sessions edit this ledger.
- Gates are sprints too, but they end with a **human decision**
  (go / narrow / stop) recorded in DECISIONS.md and an annotated git tag.
- A `narrow` or `stop` decision at any gate invalidates everything after
  it until a Replanner session rewrites the remaining sprints.

## Milestones

| ID | Name | Sprints | Exit condition |
|---|---|---|---|
| M0 | Thesis validation | S00-S05 | Day-30 gate: ≥15% over B1 on ≥1 experiment, semantic charter frozen |
| M1 | Compiler skeleton | S06-S12 | Two-node DAG through real IR+runtime; 15-program differential corpus green |
| M2 | Runtime & scheduler | S13-S15 | Safe 1-GPU parallel fan-out/fan-in via native runtime; overhead budget met |
| M3 | Integration & evidence | S16-S21 | Day-90 gate: B0-B3 evidence package, go/narrow/stop |
| M4 | v0.1 hardening & release | S22-S29 | All §24.2 gates pass; v0.1.0-preview tagged |
| M5+ | Beta → v1 | POST-V01 stub | Expanded only after S29 |

## Sprint ledger

| ID | Title | Depends on | Hardware | Status | Validated |
|---|---|---|---|---|---|
| S00 | [Project bootstrap & governance](#1) | — | CPU | done | 2026-08-11 |
| S01 | [Benchmark harness (cobra-bench v0)](#2) | S00 | CPU | not_started | — |
| S02 | [Baseline workloads & B0/B1 report](#3) | S01 | **GPU** | not_started | — |
| S03 | [Disposable whole-program tracer](#4) | S02 | **GPU** | not_started | — |
| S04 | [CUDA experiments A/B/C](#5) | S03 | **GPU** | not_started | — |
| S05 | [**GATE: day-30 go/narrow/stop**](#6) | S04 | — | not_started | — |
| S06 | [Toolchain pinning & dev container](#7) | S05=go | CPU | not_started | — |
| S07 | [MLIR dialect skeleton (CobraProgram/Effect)](#8) | S06 | CPU | not_started | — |
| S08 | [Native runtime core (CPU)](#9) | S06 | CPU | not_started | — |
| S09 | [Python extension & first capture](#10) | S07,S08 | CPU | not_started | — |
| S10 | [Trace→IR lowering, explain v0, parser fuzz](#11) | S09 | CPU | not_started | — |
| S11 | [Guards & specialization cache](#12) | S09 | CPU | not_started | — |
| S12 | [Graph breaks, fallback contract, shadow mode](#13) | S11 | CPU | not_started | — |
| S13 | [DAG scheduler + virtual-clock simulation](#14) | S08 | CPU | not_started | — |
| S14 | [CUDA runtime (streams/events/memory)](#15) | S13 | **GPU** | not_started | — |
| S15 | [Scheduler overhead benchmarks & granularity](#16) | S14 | **GPU** | not_started | — |
| S16 | [PyTorch adapter (torch.compile bridge)](#17) | S12,S14 | **GPU** | not_started | — |
| S17 | [Dataframe adapter (pandas/cuDF/Arrow)](#18) | S16 | **GPU** | not_started | — |
| S18 | [DLPack handoff & memory ownership](#19) | S16,S17 | **GPU** | not_started | — |
| S19 | [Cost model v0, profitability gate, CUDA Graphs](#20) | S15,S18 | **GPU** | not_started | — |
| S20 | [Day-90 evidence package (B0-B3)](#21) | S19 | **GPU** | not_started | — |
| S21 | [**GATE: day-90 go/narrow/stop**](#22) | S20 | — | not_started | — |
| S22 | [Effect & alias analysis hardening](#23) | S21=go | **GPU** | not_started | — |
| S23 | [Optimizer passes (parallelize/fuse/place)](#24) | S22 | **GPU** | not_started | — |
| S24 | [50-program corpus, property & metamorphic tests](#25) | S23 | **GPU** | not_started | — |
| S25 | [Fuzzing, sanitizers, failure injection](#26) | S24 | **GPU** | not_started | — |
| S26 | [CLI & developer experience (explain/doctor/docs)](#27) | S23 | CPU | not_started | — |
| S27 | [Packaging, wheels, SBOM](#28) | S26 | CPU | not_started | — |
| S28 | [v0.1 qualification (soak + benchmark gates)](#29) | S24,S25,S27 | **GPU** | not_started | — |
| S29 | [**GATE: v0.1 release review**](#30) | S28 | — | not_started | — |

## Gate summaries

- **S05 / day-30** (plan §29): at least one experiment shows a
  statistically valid ≥15% improvement over B1 with a whole-program
  mechanism; otherwise narrow the thesis before building the compiler.
- **S21 / day-90** (plan §29): no semantic divergence; ≥70% capture on one
  representative pipeline; ≥1 pipeline ≥15% over B1; a transfer boundary
  eliminated; scheduler overhead preserves gains; credible route to v0.1.
- **S29 / v0.1** (plan §24.2): all correctness, performance, and product
  gates pass with evidence; release is promoted without rebuilding.

## Changelog

- 2026-08-10: Initial roadmap created (setup session). Owner decisions:
  English artifacts, GPU available from day one, full detail through v0.1.
