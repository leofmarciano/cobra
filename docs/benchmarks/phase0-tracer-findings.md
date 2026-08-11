# Phase 0 tracer findings

This memo summarizes what the S03 disposable whole-program tracer observes in
the three frozen Phase 0 workloads.  The numbers below are taken directly from
the tracer reports in `experimental/tracer/reports/*.md` and represent a single
traced B0 run, not a statistically qualified benchmark.  Their purpose is to
identify concrete cross-library optimization opportunities that Cobra could
exploit, and to distinguish the ones a tensor-only compiler such as
`torch.compile` cannot see.

## Method

```bash
uv run python -m tracer.run --out experimental/tracer/reports
```

The tracer records call boundaries, value-identity handles, per-value metadata
(dtype, shape, device, storage id), and wall-clock durations.  It then builds a
dependency DAG and computes critical path, theoretical speedup, transfer
boundaries, and candidate fork/join parallel regions.

## 1. parquet_feature_inference

Pipeline: `read_parquet` → pandas filter/feature engineering → `to_numpy` →
torch MLP → projection.

Observed from trace:

* **Total recorded work:** ~365 ms
* **Critical path (span):** ~254 ms
* **Theoretical speedup:** ~1.44x
* **Transfer boundaries:** 6 host/device transfers, dominated by a single
  `cpu → cuda:0` move of the feature matrix (~127 ms, ~50 % of span).
* **Parallel regions:** none (the DAG is a linear chain).

### Concrete opportunities

1. **Eliminate or overlap the dataframe→tensor transfer.** The pandas
   preprocessing produces a CPU tensor via `to_numpy`, then `torch.Tensor.to`
moves it to GPU. That transfer alone is the largest single op on the critical
path. A whole-program compiler could keep the intermediate column data on GPU
(via cuDF / GPU-backed Arrow) and hand off a zero-copy or single-copy GPU buffer
to the torch MLP. The tracer records the boundary at node 17 (`torch.TensorBase.to`).

2. **Fuse pandas-derived feature kernels.** `feature_c` and the one-hot encoding
   are row-wise operations over a DataFrame. A compiler with a relational
execution path could fuse them into one kernel and avoid materializing the
intermediate DataFrame.

### What torch.compile alone cannot see

* The pandas preprocessing is outside the torch graph. `torch.compile` only
  receives the already-formed CPU tensor, so it cannot move the preprocessing
  to GPU, avoid the `to_numpy` conversion, or fuse across the library boundary.

## 2. model_ensemble

Pipeline: generate batch → two independent `nn.Module` forward passes (MLP +
TransformerEncoder) → weighted aggregation → CPU summary.

Observed from trace:

* **Total recorded work:** ~151 ms
* **Critical path (span):** ~141 ms
* **Theoretical speedup:** ~1.07x
* **Top critical-path op:** `torch.nn.functional.multi_head_attention_forward`
  (~118 ms, ~84 % of span).
* **Candidate parallel region:** fork at the shared input GPU tensor (node 2)
  and join at the final `.numpy()` output (node 509). The two branches are
  `[428, 435]`; parallelizable work is ~24 ms.

### Concrete opportunities

1. **Overlap the two model branches on separate CUDA streams.** The MLP and
   transformer branches consume the same input tensor and write disjoint output
tensors before the weighted aggregation. Running them concurrently could
reduce span by roughly the shorter branch (~17–24 ms of the 141 ms span, an
estimated ~12–17 % span reduction). The tracer explicitly names the fork/join
region in the report.

2. **Lift parameter transfers out of the measured window.** The trace shows many
   small `cpu → cuda:0` `.to` calls during forward, most likely model parameters
being moved. Pre-staging weights to GPU once (or using pinned/managed memory)
would remove this noise from steady-state inference.

### What torch.compile alone cannot see

* `torch.compile` optimizes each `forward()` independently. It has no knowledge
  that the two `model(x)` calls are independent sibling branches that can run on
  separate streams, nor that their results are only combined after both finish.
  A whole-program compiler must own the DAG across module boundaries to schedule
  this overlap.

## 3. cv_preprocess_inference_postprocess

Pipeline: synthetic images → CPU preprocessing (resize, normalize) → resnet18 on
GPU → softmax/top-k → CPU summary.

Observed from trace:

* **Total recorded work:** ~735 ms
* **Critical path (span):** ~576 ms
* **Theoretical speedup:** ~1.28x
* **Top critical-path ops:** `conv2d` and `linear` layers inside resnet18
  (~260 ms + ~95 ms + smaller convs).
* **Transfer boundaries:** 125 explicit host/device transfers, totaling ~44 ms.
  123 of them are `torch.TensorBase.to cpu → cuda:0`; only 2 are result
  `cpu()` calls back to host.
* **Device residency:** CPU preprocessing → GPU inference → CPU postprocessing.
* **Parallel regions:** none detected (linear DAG).

### Concrete opportunities

1. **Overlap CPU preprocessing with GPU inference.** The trace shows a clean
   CPU→GPU phase boundary at node 2421. A streaming compiler could start moving
preprocessed mini-batches to GPU before the whole batch is ready, overlapping
CPU preprocessing latency with GPU inference. The tracer shows the critical path
is 45 % conv2d, so hiding CPU work behind GPU work could shrink span by the
overlap amount.

2. **Pre-stage resnet18 weights on GPU.** The 123 small `cpu → cuda:0` moves
   inside resnet18 (~44 ms total) suggest weights are not resident at the start
of the traced `b0()` call. Pre-staging or using `torch.no_grad()` + pinned
parameters would eliminate this overhead in steady-state inference.

### What torch.compile alone cannot see

* The CPU preprocessing loop in `_preprocess` is ordinary Python that
  `torch.compile` never enters. It cannot fuse or move the bilinear resize/normalize
  to GPU, nor can it pipeline preprocessing with inference.
* `torch.compile` does not own weight placement across the whole program, so
  it cannot pre-stage the resnet18 parameters before the first forward call.

## Cross-workload summary

| Workload | Span | Work/span | Dominant critical-path op | Cross-library opportunity |
|---|---|---|---|---|
| parquet_feature_inference | ~254 ms | 1.44x | `torch.TensorBase.to` (feature transfer) | pandas/cuDF → torch GPU handoff |
| model_ensemble | ~141 ms | 1.07x | `multi_head_attention_forward` | two independent model branches on separate streams |
| cv_preprocess_inference_postprocess | ~576 ms | 1.28x | resnet18 `conv2d` | CPU preprocessing ↔ GPU inference overlap |

At least two of the opportunities above (parquet transfer elimination and
model_ensemble branch overlap) are invisible to `torch.compile` because they
require whole-program knowledge across library and module boundaries. These are
the targets for the S04 high-risk experiments.
