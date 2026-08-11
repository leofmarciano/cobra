# Phase 0 tracer findings

This memo summarizes what the S03 disposable whole-program tracer observes in
the three frozen Phase 0 workloads. The numbers below are taken directly from
the tracer reports in `experimental/tracer/reports/*.md` and represent a
single traced B0 run, not a statistically qualified benchmark. Their purpose
is to identify concrete cross-library optimization opportunities and to
separate measured observations from candidates that still require validation.

## Method

```bash
uv run python -m tracer.run --out experimental/tracer/reports
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

* **Total recorded work:** 409.406 ms
* **Critical path (span):** 260.439 ms
* **Theoretical speedup:** 1.57x
* **Transfer boundaries:** 6 host/device transfers totaling 137.471 ms; five
  `cpu → cuda:0` transfers account for 137.080 ms.
* **Dominant critical-path op:** `torch.TensorBase.to`, 136.209 ms (52.3% of
  the span).
* **Parallel regions:** none detected.

### Concrete opportunities

1. **Eliminate or overlap the dataframe→tensor transfer.** The pandas
   preprocessing materializes NumPy arrays and the MLP then moves the feature
   tensor to the GPU. A whole-program compiler could keep the intermediate
   column data on GPU (via cuDF / GPU-backed Arrow) and hand off a zero-copy or
   single-copy GPU buffer to torch. The largest observed boundary is the
   `torch.TensorBase.to` transfer around node 26 (with the largest transfer
   event at node 72).

2. **Fuse pandas-derived feature kernels.** `feature_c` and the one-hot encoding
   are row-wise operations over a DataFrame. A compiler with a relational
   execution path could fuse them into one kernel and avoid materializing the
   intermediate DataFrame.

The regenerated trace now also records the pandas/NumPy boundaries explicitly:
`pandas.DataFrame.to_numpy`, `numpy.mean`, `numpy.std`, `numpy.where`, and
`numpy.percentile`. This makes the conversion and projection costs visible to
later whole-program passes.

### What torch.compile alone cannot see

The pandas preprocessing is outside the torch graph. `torch.compile` only
receives the already-formed CPU tensor, so it cannot move preprocessing to the
GPU, avoid the `to_numpy` conversion, or fuse across the library boundary.

## 2. model_ensemble

Pipeline: generate batch → two independent `nn.Module` forward passes (MLP +
TransformerEncoder) → weighted aggregation → CPU summary.

Observed from trace:

* **Total recorded work:** 200.145 ms
* **Critical path (span):** 180.377 ms
* **Theoretical speedup:** 1.11x
* **Top critical-path op:** `torch.nn.functional.multi_head_attention_forward`,
  142.165 ms (78.8% of the span).
* **Transfer boundaries:** 38 transfers totaling 3.378 ms.
* **Candidate parallel regions:** 272 coarse fork/join candidates. The largest
  reported candidate is a `torch._C._nn.linear` node 436 →
  `torch.TensorBase.transpose` node 457 region, with only 18.641 us of
  estimated overlap.

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
   35 `cpu → cuda:0` transfers totaling 3.012 ms. Pre-staging weights to GPU
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

* **Total recorded work:** 1.183 s
* **Critical path (span):** 949.132 ms
* **Theoretical speedup:** 1.25x
* **Top critical-path operations:** `conv2d` at 491.940 ms and `linear` at
  109.616 ms.
* **Transfer boundaries:** 125 transfers totaling 75.177 ms; 123 are
  `cpu → cuda:0` moves totaling 74.839 ms, and 2 return to CPU.
* **Device residency:** CPU preprocessing → GPU inference → CPU postprocessing,
  with the main GPU boundary at node 2421.
* **Candidate parallel regions:** 1,939 coarse candidates. The top candidate
  is a `relu` → `add_` region with 5.680 ms of estimated overlap, not a
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
| parquet_feature_inference | 260.439 ms | 1.57x | `torch.TensorBase.to` | pandas/cuDF → torch GPU handoff |
| model_ensemble | 180.377 ms | 1.11x | `multi_head_attention_forward` | two model branches on separate streams |
| cv_preprocess_inference_postprocess | 949.132 ms | 1.25x | `conv2d` | CPU preprocessing ↔ GPU inference pipeline |

The parquet handoff and the model-ensemble branch schedule remain promising
S04 high-risk experiments because they cross pandas/NumPy/torch or separate
module boundaries. The tracer reports expose where to validate them, but the
reported candidate regions are intentionally heuristic and must not be
presented as achieved speedups.
