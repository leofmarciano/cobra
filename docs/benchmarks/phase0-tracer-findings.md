# Phase 0 tracer findings

This memo summarizes what the S03 disposable whole-program tracer observes in
the three frozen Phase 0 workloads. The numbers below are taken directly from
the tracer reports in `experimental/tracer/reports/*.md` and represent a
single traced B0 run, not a statistically qualified benchmark. Their purpose
is to identify concrete cross-library optimization opportunities and to
separate measured observations from candidates that still require validation.

## Method

```bash
uv run python -m tracer.run --workload all --out experimental/tracer/reports
```

The tracer records call boundaries, value-identity handles, per-value metadata
(dtype, shape, device, storage id), and wall-clock durations. It then builds a
dependency DAG and computes critical path, theoretical speedup, transfer
boundaries, and candidate fork/join parallel regions. For CUDA-valued torch
calls, the recorder synchronizes before taking the end timestamp so the
reported duration includes device completion.

## 1. parquet_feature_inference

Pipeline: `read_parquet` → pandas filter/feature engineering → `to_numpy` →
torch MLP → projection.

Observed from trace:

* **Total events:** 108
* **Total recorded work:** 400.609 ms
* **Critical path (span):** 389.180 ms
* **Theoretical speedup:** 1.03x
* **Transfer boundaries:** 6 host/device transfers totaling 134.757 ms; five
  `cpu → cuda:0` transfers account for 134.295 ms.
* **Dominant critical-path op:** `torch.TensorBase.to`, 133.415 ms (34.3% of
  the span); `pandas.read_parquet` is second at 97.849 ms (25.1%).
* **Candidate parallel regions:** 8 coarse candidates; the largest reported
  overlap opportunity is 4.545 ms and is not a validated schedule.

### Concrete opportunities

1. **Eliminate or overlap the dataframe→tensor transfer.** The pandas
   preprocessing materializes NumPy arrays and the MLP then moves the feature
   tensor to the GPU. A whole-program compiler could keep the intermediate
   column data on GPU (via cuDF / GPU-backed Arrow) and hand off a zero-copy or
   single-copy GPU buffer to torch. The largest observed boundary is the
   `torch.TensorBase.to` transfer around node 47 (with the largest transfer
   event at node 93).

2. **Fuse pandas-derived feature kernels.** `feature_c` and the one-hot encoding
   are row-wise operations over a DataFrame. A compiler with a relational
   execution path could fuse them into one kernel and avoid materializing the
   intermediate DataFrame.

The regenerated trace now also records the pandas/NumPy/torch boundaries
explicitly: the boolean filter (`Series.__gt__`, `Series.__and__`,
`Series.notna`, and `DataFrame.reset_index`), `DataFrame.__init__`,
`DataFrame.to_numpy`, `numpy.mean`, `numpy.std`, `numpy.equal`,
`numpy.where`, `numpy.subtract`, `numpy.divide`, and `torch.from_numpy`.
Together these events connect filtering, normalization, frame reconstruction,
and tensor conversion for later whole-program passes.

Storage handles still alias read-only views for mutation ordering, while the
tracer's logical handles retain view lineage; the regenerated DAG therefore
includes the view producer before consumers such as `.to(...)`.

### What torch.compile alone cannot see

The pandas preprocessing is outside the torch graph. `torch.compile` only
receives the already-formed CPU tensor, so it cannot move preprocessing to the
GPU, avoid the `to_numpy` conversion, or fuse across the library boundary.

## 2. model_ensemble

Pipeline: generate batch → two independent `nn.Module` forward passes (MLP +
TransformerEncoder) → weighted aggregation → CPU summary.

Observed from trace:

* **Total events:** 514
* **Total recorded work:** 157.118 ms
* **Critical path (span):** 145.176 ms
* **Theoretical speedup:** 1.08x
* **Top critical-path op:** `torch.nn.functional.multi_head_attention_forward`,
  118.332 ms (81.5% of the span).
* **Transfer boundaries:** 38 transfers totaling 3.065 ms.
* **Candidate parallel regions:** 60 coarse fork/join candidates. The largest
  reported candidate is a `torch.TensorBase.to` node 2 →
  `torch.TensorBase.add` node 503 region, with only 1.067 ms of estimated
  overlap.

The source workload does contain two independent model calls, but this
call-boundary trace does not yet isolate that high-level pair as one validated
region: setup operations and storage-identity reuse produce many smaller
candidates. The candidate list is therefore a discovery signal, not a measured
stream-overlap result.

### Concrete opportunities

1. **Validate overlap of the two model branches on separate CUDA streams.** The
   MLP and transformer consume the same input and write disjoint outputs before
   weighted aggregation. A whole-program scheduler can test whether concurrent
   execution reduces span; the current report alone does not claim a specific
   speedup.

2. **Lift parameter transfers out of the measured window.** The trace contains
   35 `cpu → cuda:0` transfers totaling 2.779 ms. Pre-staging weights to GPU
   once, or using pinned/managed memory where appropriate, could remove this
   setup cost from steady-state inference.

### What torch.compile alone cannot see

`torch.compile` optimizes each `forward()` independently. It has no knowledge
that the two model calls are sibling branches that could run on separate
streams, nor that their results are combined only afterward. A whole-program
compiler must own the DAG across module boundaries to schedule that overlap.

## 3. cv_preprocess_inference_postprocess

Pipeline: synthetic images → CPU preprocessing (resize, normalize) → resnet18
on GPU → softmax/top-k → CPU summary.

Observed from trace:

* **Total events:** 3,345
* **Total recorded work:** 864.763 ms
* **Critical path (span):** 620.116 ms
* **Theoretical speedup:** 1.39x
* **Top critical-path operations:** `conv2d` at 278.565 ms and `linear` at
  99.024 ms.
* **Transfer boundaries:** 125 transfers totaling 65.290 ms; 123 are
  `cpu → cuda:0` moves totaling 65.014 ms, and 2 return to CPU.
* **Device residency:** CPU preprocessing → GPU inference → CPU postprocessing,
  with the main GPU boundary at node 2677.
* **Candidate parallel regions:** 2,931 coarse candidates. The top candidate
  is an `add_` → `add_` region with 6.207 ms of estimated overlap, not a
  validated end-to-end CPU/GPU pipeline overlap.

### Concrete opportunities

1. **Overlap CPU preprocessing with GPU inference.** The clean CPU→GPU phase
   boundary suggests a streaming compiler could move preprocessed mini-batches
   while the GPU consumes earlier ones. This must be measured with a batched
   schedule; the single-batch trace establishes the boundary but not the gain.

2. **Pre-stage resnet18 weights on GPU.** The many small `cpu → cuda:0` moves
   likely include parameter placement during model construction. Pre-staging
   weights before the steady-state window could remove that setup overhead.

### What torch.compile alone cannot see

The CPU preprocessing loop in `_preprocess` is ordinary Python that
`torch.compile` never enters. It cannot fuse or move bilinear resize/normalize
to GPU, pipeline preprocessing with inference, or own weight placement across
the whole program.

## Cross-workload summary

| Workload | Span | Work/span | Dominant critical-path op | Cross-library opportunity |
|---|---:|---:|---|---|
| parquet_feature_inference | 389.180 ms | 1.03x | `torch.TensorBase.to` | pandas/cuDF → torch GPU handoff |
| model_ensemble | 145.176 ms | 1.08x | `multi_head_attention_forward` | two model branches on separate streams |
| cv_preprocess_inference_postprocess | 620.116 ms | 1.39x | `conv2d` | CPU preprocessing ↔ GPU inference pipeline |

The parquet handoff and the model-ensemble branch schedule remain promising
S04 high-risk experiments because they cross pandas/NumPy/torch or separate
module boundaries. The tracer reports expose where to validate them, but the
reported candidate regions are intentionally heuristic and must not be
presented as achieved speedups.
