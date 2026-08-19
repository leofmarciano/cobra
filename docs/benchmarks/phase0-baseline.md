# Phase 0 baseline report

This report records the B0 (plain eager) and B1 (strongest automatic composition)
measurements for the three prototype workloads defined in sprint S02.  These
numbers are the enemy Cobra must beat at S05/S21.

## Host and software environment

All measurements were captured on the primary GPU host recorded in
`orchestration/STATE.md`:

| Item | Value |
|---|---|
| Host | WSL2 Ubuntu 24.04.1 LTS (`DESKTOP-P3JA7HS`) |
| Kernel | 6.6.87.2-microsoft-standard-WSL2 |
| CPU | Intel Core i9-10900F (12 vCPU) |
| RAM | 15.62 GiB |
| GPU | NVIDIA GeForce RTX 3080, 10 GiB |
| Driver | 591.86 |
| CUDA compute capability | 8.6 (sm_86) |
| GPU persistence mode | Enabled |
| GPU power limit | 320 W |

Framework pins (from `support-matrix.yaml` and `benchmarks/pipelines/pyproject.toml`):

| Package | Version |
|---|---|
| Python | 3.13.12 |
| torch | 2.13.0 |
| torchvision | 0.28.0 |
| numpy | 2.4.6 |
| pandas | 2.3.3 |
| pyarrow | 23.0.1 |
| cudf-cu13 | 26.6.0 |
| nvidia-cuda-nvcc | 13.0.88 |

Environment validation:

```bash
uv run cobra-bench doctor --strict --output artifacts/environment/primary-host.json
```

## Suite definition

The three workloads are defined in
`benchmarks/suites/phase0.yaml`:

1. `parquet_feature_inference` — synthetic Parquet → pandas/cudf feature
   engineering → small torch MLP → projection.
2. `model_ensemble` — one batch → independent MLP + TransformerEncoder branches
   → weighted aggregation.
3. `cv_preprocess_inference_postprocess` — synthetic images → CPU preprocessing
   (resize/normalize) → torchvision resnet18 → top-k/threshold postprocess.

B0 is plain eager Python. B1 applies `torch.compile(mode=default, fullgraph=False)`
to the model(s) and uses `cudf.pandas.install()` for the Parquet/dataframe workload.
For the warm phase, both variants cache model construction outside measured
samples; only B1 adds compilation and transparent cuDF acceleration. No manual
restructuring was performed.

## Reproducing the measurements

The timing artifacts were regenerated from commit
`7b3d6bfd36cf661c1c05e6746f77c9c12298decb` after the persistent worker and
symmetric warm-cache changes. `cobra-bench run` records the measured Git
revision and doctor-collected host/CUDA/software metadata in
`artifacts/raw/phase0/manifest.yaml`; the exact host record is also kept in
`artifacts/environment/primary-host.json`. The commands were:

```bash
# Correctness qualification (must pass before timing is valid per §33.4)
uv run cobra-bench verify \
  --suite benchmarks/suites/phase0.yaml \
  --variants b0,b1 \
  --output artifacts/correctness/phase0

# Warm timing, 30 samples per workload×variant, randomized order
uv run cobra-bench run \
  --suite benchmarks/suites/phase0.yaml \
  --variants b0,b1 \
  --phase warm \
  --output artifacts/raw/phase0 \
  --seed 42

# Statistical summary with bootstrap 95% CIs
uv run cobra-bench analyze \
  --input artifacts/raw/phase0 \
  --output artifacts/analysis/phase0 \
  --seed 42
```

Raw samples, analysis outputs, and Nsight Systems traces are committed under
`artifacts/`. The B1 parquet trace profiles the persistent worker body
directly (`_b1_inprocess`) so the isolated child is visible to Nsight Systems;
the timing samples still use the public `b1()` entrypoint.

## Absolute timing results

| Workload | Variant | Median (ms) | p95 (ms) | p99 (ms) | CV | Speedup vs B0 | 95% CI | Significant |
|---|---|---:|---:|---:|---:|---:|---|---:|
| parquet_feature_inference | b0 | 25.065 | 27.108 | 27.725 | 0.040 | 1.000x | [1.000x, 1.000x] | no |
| parquet_feature_inference | b1 | 52.391 | 65.816 | 68.771 | 0.097 | 0.478x | [0.455x, 0.495x] | yes |
| model_ensemble | b0 | 8.255 | 8.736 | 8.837 | 0.038 | 1.000x | [1.000x, 1.000x] | no |
| model_ensemble | b1 | 8.686 | 9.716 | 9.924 | 0.061 | 0.950x | [0.901x, 0.977x] | yes |
| cv_preprocess_inference_postprocess | b0 | 26.343 | 31.815 | 33.251 | 0.077 | 1.000x | [1.000x, 1.000x] | no |
| cv_preprocess_inference_postprocess | b1 | 25.743 | 27.194 | 27.348 | 0.035 | 1.023x | [0.998x, 1.064x] | no |

**Suite geometric-mean speedup (B1 vs B0):** 0.775x — i.e. the automatic tools
are slower than eager Python on average for these particular small workloads.
This is expected: the workloads are intentionally small and synchronous, so
compilation and cuDF acceleration overheads are not amortized. The important
product baseline is the B1 number Cobra must beat.

## Nsight Systems trace capture

One representative iteration per workload×variant was profiled with Nsight
Systems CLI 2024.4.1. For the updated parquet pair, B0 was profiled through
`b0()` and B1 through `_b1_inprocess()` with the worker environment marker set;
this captures the code executed by the persistent child without folding child
process startup into the trace. Because this host is WSL2, GPU-side timestamps
were not reliably converted by default; the workaround documented by NVIDIA
was applied:

```bash
mkdir -p "$(dirname "$(nsys -z)")"
echo "CuptiUseRawGpuTimestamps=false" > "$(nsys -z)"
```

The trace command used for ordinary variants was:

```bash
nsys profile -t cuda,nvtx,osrt \
  -o artifacts/traces/phase0/<workload>-<variant> \
  <venv-python> -c "from cobra_pipelines.<workload> import <variant>; <variant>()"
```

For the isolated parquet B1 worker, the equivalent trace command was:

```bash
COBRA_PARQUET_B1_WORKER=1 nsys profile -t cuda,nvtx,osrt \
  -o artifacts/traces/phase0/parquet_feature_inference-b1 \
  <venv-python> -c \
  "from cobra_pipelines.parquet_feature_inference import _b1_inprocess; _b1_inprocess()"
```

Captured trace files:

| Workload | Variant | Trace file |
|---|---|---|
| parquet_feature_inference | b0 | `artifacts/traces/phase0/parquet_feature_inference-b0.nsys-rep` |
| parquet_feature_inference | b1 | `artifacts/traces/phase0/parquet_feature_inference-b1.nsys-rep` |
| model_ensemble | b0 | `artifacts/traces/phase0/model_ensemble-b0.nsys-rep` |
| model_ensemble | b1 | `artifacts/traces/phase0/model_ensemble-b1.nsys-rep` |
| cv_preprocess_inference_postprocess | b0 | `artifacts/traces/phase0/cv_preprocess_inference_postprocess-b0.nsys-rep` |
| cv_preprocess_inference_postprocess | b1 | `artifacts/traces/phase0/cv_preprocess_inference_postprocess-b1.nsys-rep` |

Machine-readable summaries were exported with:

```bash
nsys stats --report cuda_gpu_kern_sum --report cuda_api_sum --report osrt_sum \
  --format csv --output artifacts/traces/phase0/summaries/<name>.csv \
  artifacts/traces/phase0/<name>.nsys-rep
```

> **Note on OS-runtime summaries:** `osrt_sum` aggregates wall-clock time
> across all threads.  On B1 runs, large `pthread_cond_wait` totals reflect
> background PyTorch/Triton worker threads sleeping while waiting for work, not
> time on the critical path.  For bottleneck analysis we therefore focus on the
> CUDA API path (launches, allocations, synchronizations) and the GPU kernel
> trace.

## Bottleneck analysis per workload

### 1. parquet_feature_inference

**Observation:** B1 is ~52% slower than B0 (52.4 ms vs 25.1 ms). Both variants
reuse their eager/compiled MLP across warm samples; B1 still pays the isolated
cuDF dispatch and worker path for this small 100k-row workload. The B1 run uses
`cudf.pandas` for dataframe operations and `torch.compile` for the MLP.

**Where the time goes (from `parquet_feature_inference-b1.nsys-rep`):**

- **CUDA API / library loading dominates:** in the updated B1 worker trace,
  `cuLibraryLoadData` takes ~141.6 ms, `cudaFree` ~141.4 ms,
  `cudaLaunchKernel` ~105.8 ms, `cudaMalloc` ~46.1 ms, and host allocation
  calls ~40.6 ms. These are initialization/teardown costs in the representative
  worker invocation, not costs silently included in every warm sample.
- **GPU kernels remain small:** the updated trace spends about 5.2 ms in GPU
  kernels. The largest are cuDF Parquet string-offset preprocessing (~2.04 ms),
  the MLP CUTLASS kernel (~0.93 ms), and the fused MLP addmm/relu (~0.82 ms).
- **The warm wall-time gap is the dataframe/dispatch path:** persistent caching
  removes repeated process and compilation setup from the measured samples, but
  cuDF dispatch and Parquet feature work still cost more than the eager B0 path
  for this small 100k-row workload.

**Interpretation:** For 100k rows the dataframe path is not large enough to
amortize cuDF dispatch costs, and the MLP is too small for `torch.compile` to
pay for itself. Cobra's opportunity here is to keep the worker resident across
larger batches and fuse the CPU→GPU handoff, not to further optimize the
already-fast GPU kernels.

### 2. model_ensemble

**Observation:** B1 is ~5% slower than B0 (8.7 ms vs 8.3 ms). Both variants
reuse their two eager branches across warm samples, while both MLP and
TransformerEncoder branches are `torch.compile`d in B1.

**Where the time goes (from `model_ensemble-b1.nsys-rep`):**

- **Compiled kernels are larger:** the top GPU kernels are `RowwiseMomentsCUDAKernel`
  (~33.7 ms, transformer layer norm), and several CUTLASS gemms (~6.8 ms, ~6.3 ms,
  ~5.9 ms).  In B0 the same categories total only ~7 ms of kernel time.
- **Synchronization overhead appears:** B1 issues 38 `cudaStreamSynchronize`
  calls (~7 ms) versus zero in B0.  `torch.compile` with the default Inductor
  backend sometimes inserts stream synchronization fences.
- **Library loading is still present:** `cuLibraryLoadData` (~83 ms) and
  `cuModuleLoad` (~7 ms) are non-trivial, though spread across the trace.

**Interpretation:** The two branches are independent (proven in T2), but they
run serially in B0/B1 on the default CUDA stream.  Cobra's parallel-branch
scheduler (Experiment A, §29) is the obvious lever: overlapping the MLP and
Transformer branches could recover the ~30-35 ms of serialized GPU work.  The
stream synchronizations in B1 are also a target: Cobra should keep the program
on the critical path and minimize fence operations.

### 3. cv_preprocess_inference_postprocess

**Observation:** B1 is ~2.3% faster than B0 (25.7 ms vs 26.3 ms), and the 95%
interval crosses 1.0x. Both variants reuse their ResNet18 across warm samples;
the compiled path is close to parity for this sample set, so no speedup is
claimed.

**Where the time goes (from `cv_preprocess_inference_postprocess-b1.nsys-rep`):**

- **CPU preprocessing dominates wall time:** the inference kernels total ~55 ms
  (CUTLASS/CUDNN convolutions, batch-norm, relu), but the measured wall time is
  ~228 ms.  The remaining ~170 ms is the CPU bilinear resize, permute, and
  normalization in `_preprocess`.
- **B1 has better GPU utilization:** B1 spends ~55 ms in compiled GPU kernels
  (top kernels include `convertTensor_kernel` ~27 ms, CUTLASS fprop ~21 ms,
  and Triton fused batch-norm+relu kernels) versus only ~5 ms of kernel time in
  B0.  The eager B0 run appears launch-bound: `cudaLaunchKernel` calls add up to
  ~88 ms of API time, while B1 reduces launch overhead by fusing operations.
- **Memory transfers are modest:** `cudaMemcpyAsync` totals ~11 ms in both B0
  and B1, which matches the single H2D transfer of the preprocessed batch.

**Interpretation:** This workload is CPU-preprocessing-bound.  Cobra's
opportunity is to overlap CPU preprocessing of batch N+1 with GPU inference of
batch N, or to move the resize/normalize pipeline to the GPU.  The B1 GPU trace
shows that once the data reaches the GPU, compiled kernels are already
reasonably efficient.

## Anti-pattern check (§33.11)

- No performance claim is made from a subset smaller than the full suite.
- All timing samples include per-sample correctness checks (the harness oracle
  ran during `cobra-bench run` with `--no-oracle` not used).
- No test tolerance or assertion was weakened to make results pass.
- The report links to raw artifacts (JSONL samples, analysis CSV/JSON/Markdown,
  and `.nsys-rep` traces) rather than hand-entered numbers.

## Files to inspect

- Raw samples: `artifacts/raw/phase0/samples.jsonl`
- Statistical summary: `artifacts/analysis/phase0/summary.md`
- Confidence intervals: `artifacts/analysis/phase0/confidence_intervals.csv`
- Environment record: `artifacts/environment/primary-host.json`
- Nsight traces: `artifacts/traces/phase0/*.nsys-rep`
- Nsight CSV summaries: `artifacts/traces/phase0/summaries/*.csv`
