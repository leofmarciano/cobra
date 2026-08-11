# POST-V0.1 ROADMAP — beta and v1 stubs

> These are milestone STUBS, not sprints. They are intentionally not
> detailed: the S29 gate + retrospective will change them. Expansion
> into real sprint files happens via `prompts/P4-replan.md` after v0.1
> ships, using the plan sections cited below as the source of truth.

## M5 — Coverage & product hardening (plan Phase 4, §23)

Entry: v0.1.0-preview shipped; beta replan decision recorded.
Plan sections: §23 Phase 4, §24.3 (beta gates as target).

Candidate sprint themes (to be sized at replan):
- Dynamic-shape guards + guard widening (recompilation-storm economics)
- Expanded PyTorch + dataframe operation coverage (coverage.yaml driven)
- Typed scalar / simple NumPy regions lowered to LLVM CPU (§14.2)
- More generated Triton kernels where vendor/Inductor is inadequate
  (§9.4 order, each kernel family benchmarked)
- Memory planner v2 (lifetime-overlap reuse, §11.4 full)
- Compile-time budget management
- AOT `.cobra` artifact prototype (§17.5) + artifact fuzzing
- Remote-cache protocol draft (§22 security posture first)
- Telemetry (opt-in, §22.5 privacy contract)
- Design-partner workload ingestion kit + shadow-mode trials (2 partners)

## M6 — Multi-GPU, experimental training, beta (plan Phase 5, §23)

Entry: M5 exit criteria (§23 Phase 4: 2 partners in shadow mode, stable
fallback boundary, native CPU regions justified).
Plan sections: §23 Phase 5, §12.5, §24.3 (all beta gates).

Candidate sprint themes:
- Same-node multi-GPU placement + peer-to-peer transfer planning
- NCCL collective representation + ordering (§19.12 multi-GPU rows
  un-skip here)
- Independent-branch multi-GPU execution + topology awareness
- Experimental forward/backward capture (gradient + optimizer-state
  differential tests, §9.6 beta scope)
- Expanded CUDA architecture matrix; 72h/48h soak qualification
- Partner canary controls + rollback drills
- Beta gates (§24.3) → GATE sprint with human sign-off

## M7 — Stable APIs, AOT, v1 (plan Phase 6, §23)

Entry: beta shipped + 30-day partner canary clean.
Plan sections: §23 Phase 6, §24.4 (v1 gates), §12.7/§15.3 (C ABI),
§26.8 (governance), §22 (independent security review).

Candidate sprint themes:
- Stable public Python API + semver; stable C plugin ABI
- Versioned AOT artifact format + JIT/AOT parity tests
- Qualified CUDA Tile backend OR evidence-based deferral (§14.3)
- Native CPU region backend qualified
- Signed artifact workflow + trust policies (§22.3)
- Production resource controls; deterministic mode qualification
- Independent security assessment; LTS/patch process
- v1 gates (§24.4) → GATE sprint

## Standing reminders for the replanner

- Re-read §28 (risks) and §28.1 (stop conditions) at every milestone
  boundary — narrowing stays on the table forever.
- Training must not consume the roadmap (§28 risk table) — it graduates
  feature-by-feature through its own gates.
- NVIDIA engagement package (§27.4) becomes relevant the moment three
  real workloads show B1-relative wins — likely mid-M5. Flag to the
  human when the evidence exists.
