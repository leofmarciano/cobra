# S16 — PyTorch adapter (torch.compile bridge)

| Field | Value |
|---|---|
| GitHub issue | #17 |
| Milestone | M3 — Integration & evidence |
| Depends on | S12, S14 (done) |
| Hardware | **NVIDIA GPU required** |
| Estimated sessions | 3-4 |
| Plan sections | §9.1-9.5, §35 Epic 5, §19.9 (subset), §32 refs 9-12 |

## Objective

Capture PyTorch regions without competing with PyTorch: Cobra registers
as the orchestration layer, delegates tensor-region compilation to
TorchInductor via the supported custom-backend interface, and schedules
independent regions on the S14 runtime. This is the sprint where
`model_ensemble` branches overlap through REAL Cobra machinery.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §9.1 (principle), §9.2 (adapter paths +
   recorded fields), §9.3 (backend table), §9.5 (math modes), §35
   Epic 5 acceptance
3. `capture/graph.py`, `capture/guards.py`, reason registry (S11/S12)
4. PyTorch custom-backend docs (fetch selectively; pinned torch version
   from support-matrix.yaml)

## Out of scope

- Training/autograd (beta). Triton kernel GENERATION (S19+). AOT/export
  path (§9.2 path 2 — post-v0.1 artifact work). Dynamic-shape guard
  WIDENING (S22+; exact-shape guards here). cuDF (S17).

## Tasks

### T1 — Adapter registration + tensor proxy
- [ ] Do: `python/cobra_compiler/adapters/torch/`: tensor values become
  Cobra proxies carrying §9.2 metadata (dtype, shape, stride, device,
  requires_grad, storage identity, version counter); adapter registers
  torch callables/modules with the capture registry; adapter versioned
  + independently disableable (flag `cobra.adapters.torch.enabled`).
- Accept: capture of a torch-using function produces IR with tensor
  metadata attrs; disable flag restores pure-eager behavior (test).

### T2 — Region handoff to TorchInductor
- [ ] Do: contiguous captured torch regions become "external compiled
  tensor region" nodes (§7.2 `cobra.tensor` external-region op —
  introduce the minimal `cobra.tensor` dialect op here); compile each
  region through `torch.compile` w/ Inductor as the region backend;
  cache compiled callables keyed by S11 cache keys (tensor guards now
  supply REAL values: dtype/shape/stride/device + model param
  identity/version hash — §6.4).
- Accept: a two-op tensor chain compiles once, cache-hits on second
  call, recompiles on dtype change, falls back on guard-budget
  exhaustion (tests for all four).

### T3 — Graph-break translation + alias/mutation safety
- [ ] Do: torch-side graph breaks (dynamo) surface as Cobra reason
  codes (`GB-TORCH-*`, mapped table committed); in-place ops
  (`add_`, `relu_` etc.) recorded as writes to storage alias sets
  (§8.2) → scheduler serializes conflicts; unknown torch ops → S12
  fallback path.
- Accept: mutation test — two branches sharing a tensor where one
  mutates NEVER overlap (simulation assertion + 1000-run GPU test);
  dynamo break on unsupported code lands as a diagnosed Cobra break.

### T4 — Branch scheduling on the real runtime
- [ ] Do: wire captured independent regions through S13/S14: each
  compiled region = one schedulable task with stream affinity; joins
  via events; output tensors correctly stream-synchronized before
  Python sees them (temporary conservative sync at boundary — S18
  refines ownership).
- Accept: `model_ensemble` end-to-end through `@cobra.compile` on GPU:
  outputs match eager (oracle), nsys shows branch overlap, exception
  injection follows §8.3 order.

### T5 — Correctness matrix (v0.1 subset of §19.9)
- [ ] Do: differential tests over the supported-op subset: dtypes
  {fp16, bf16, fp32, int64, bool} × layouts {contiguous, transposed,
  sliced} × shapes {empty, scalar-like, small, large-ish} × alias
  {independent, shared-input, view}; per-op-family tolerances document-
  ed; corpus programs added to `test/Differential/`.
- Accept: matrix lane green on GPU host; every skip has a reason
  string; tolerances match S02 oracle conventions.

## Validation

```bash
uv run pytest test/python/adapters/torch -q
uv run pytest test/Differential -q -m torch
uv run python examples/ensemble_overlap.py   # prints per-branch streams + oracle pass
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted (Epic 5: compile-through-backend, safe dynamic
      guard failure, alias/empty/non-contiguous parity, independent
      disable — all tested)
- [ ] nsys overlap evidence committed; adapter version pin recorded in
      support-matrix.yaml
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S17 mirrors this shape for dataframes. S18 replaces T4's conservative
boundary syncs with real ownership tokens. S19 decides WHERE regions run
(cost model) — T4 currently uses naive round-robin placement.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
