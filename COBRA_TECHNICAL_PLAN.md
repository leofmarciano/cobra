# Project Cobra
## Complete Technical Plan for an AI-Native Whole-Program Python Compiler and Heterogeneous Parallel Runtime

**Document status:** Architecture and execution plan, Draft 1.0  
**Last updated:** 2026-08-10  
**Project name:** Cobra  
**Primary audience:** Compiler engineers, GPU engineers, AI infrastructure engineers, platform engineers, technical founders, design partners, and investors performing technical diligence  
**Initial target:** Linux, CPython, NVIDIA CUDA, single-node CPU and GPU systems  
**Recommended core license:** Apache-2.0 WITH LLVM-exception  

---

## Table of contents

1. Executive summary
2. Product definition
3. Product experience
4. Technical positioning and build-versus-integrate decision
5. System architecture
6. Frontend and capture model
7. Intermediate representation design
8. Effect, alias, and parallelism model
9. Tensor execution strategy
10. Dataframe and relational execution strategy
11. Interoperability and memory model
12. Runtime architecture
13. Cost model and autotuning
14. Backends and code generation roadmap
15. Implementation languages and toolchain
16. Repository, build, and packaging design
17. Public product surface
18. TDD operating model
19. Complete test strategy
20. Benchmark program
21. Continuous integration and release engineering
22. Security, privacy, and supply-chain design
23. End-to-end engineering roadmap
24. Formal release gates
25. Team and operating model
26. Licensing, governance, and commercial model
27. NVIDIA alignment and engagement plan
28. Principal risks and mitigations
29. First 90 days execution plan
30. Definition of Done
31. Recommended final product thesis
32. Primary technical references
33. Benchmark execution runbook
34. Test and CI command matrix
35. v0.1 issue-ready epic backlog
36. Approval record

---

## 1. Executive summary

Cobra is an AI-native whole-program optimizer and heterogeneous parallel runtime for ordinary Python AI workloads.

Its purpose is not merely to translate Python into C or machine code. Its purpose is to transform a Python AI program into the most efficient correct execution plan available for the target machine. Cobra will discover data dependencies, preserve side effects, identify safe parallel regions, reduce unnecessary memory movement, select specialized libraries or generated kernels, and schedule work across CPU cores, CUDA streams, and multiple GPUs.

The product thesis is:

> Developers should be able to write normal Python AI pipelines while Cobra automatically derives a parallel, memory-aware, hardware-specific execution plan.

A representative input is:

```python
import cobra_compiler as cobra
import pandas as pd

@cobra.compile(mode="inference")
def score_customers(path, model_a, model_b):
    df = pd.read_parquet(path)
    df = df[df["active"]]
    features = build_features(df)

    risk = model_a(features)
    propensity = model_b(features)

    return combine(risk, propensity)
```

Cobra should eventually derive a plan similar to:

```text
Parquet scan
    |
GPU-compatible filtering and feature preparation
    |
zero-copy tensor handoff
    |
    +---------------------+
    |                     |
model_a on GPU 0      model_b on GPU 1
    |                     |
    +----------+----------+
               |
            combine
```

The first release must not attempt to support every Python feature or replace CPython. Cobra will begin as a conservative optimizer hosted by CPython:

1. Supported operations are captured into a lazy graph.
2. Unknown operations become correctness barriers and execute through normal Python.
3. Every compiled specialization is protected by runtime guards.
4. Incorrect or unprofitable regions fall back to the strongest known baseline.
5. No optimization is accepted without differential correctness tests and measured benchmark evidence.

The recommended implementation strategy is:

- **Compiler and runtime core:** C++20.
- **Intermediate representation:** MLIR with a small set of Cobra dialects and extensive reuse of standard MLIR dialects.
- **Python frontend and adapters:** Python plus a thin C extension.
- **Initial tensor backend:** PyTorch graph capture plus TorchInductor and Triton integration.
- **Initial dataframe backend:** pandas-compatible capture plus cuDF and CPU fallback.
- **NVIDIA-native kernel path:** CUDA Tile IR or CUDA Tile C++ after the backend is sufficiently stable for Cobra's supported matrix.
- **CPU native code generation:** LLVM for statically typed scalar and loop regions, introduced after v0.1.
- **Interoperability:** DLPack for tensors and Apache Arrow C Data and C Device interfaces for columnar data.
- **Initial platform scope:** Linux x86-64, one NVIDIA GPU, inference and batch pipelines.
- **Beta scope:** multiple GPU architectures, multi-GPU branch scheduling, broader dataframe and NumPy capture, experimental training.
- **v1 scope:** stable public APIs, single-node multi-GPU, production hardening, AOT artifacts, native CPU regions, NVIDIA tile backend, and an enterprise-ready compatibility and security posture.

The principal commercial value is measured in GPU-seconds, throughput, latency, and infrastructure cost, not in isolated language microbenchmarks.

---

## 2. Product definition

### 2.1 Mission

Make ordinary Python AI programs execute as optimized heterogeneous graphs without requiring developers to manually write CUDA streams, device placement, ranks, collectives, kernel fusion, memory transfer logic, or distributed orchestration.

### 2.2 Core value propositions

Cobra must deliver value in five dimensions:

1. **Task-level parallelism:** independent models, preprocessors, data reads, feature branches, and postprocessors may execute concurrently.
2. **Operation-level optimization:** tensor and dataframe regions are delegated to or generated for specialized engines.
3. **Memory optimization:** values remain on the appropriate device, unnecessary copies are eliminated, and compatible buffers are reused.
4. **Hardware placement:** CPU, GPU, and multi-GPU placement is selected using a cost model and resource constraints.
5. **Operational explainability:** every graph break, fallback, transfer, fusion, placement decision, and guard is visible to the user.

### 2.3 Initial target users

The initial product should target teams with heterogeneous Python AI pipelines rather than teams whose workload is already a single, well-optimized training graph.

Priority users:

- AI inference platform teams.
- Recommendation and ranking teams.
- Computer vision pipeline teams.
- RAG ingestion and retrieval infrastructure teams.
- Fraud and risk teams combining dataframes, rules, and models.
- Multimodal and multi-model inference teams.
- Batch embedding and feature engineering teams.
- Teams paying significant GPU infrastructure costs while observing low or bursty GPU utilization.

### 2.4 Workloads with the highest expected value

Cobra should prioritize pipelines containing several of the following characteristics:

- pandas or dataframe preprocessing before GPU inference.
- Repeated CPU-to-GPU and GPU-to-CPU transitions.
- Multiple independent models or model branches.
- Many small GPU kernels and visible launch gaps.
- Python orchestration between native library calls.
- Dynamic but recurring shapes.
- Expensive preprocessing that can overlap with GPU execution.
- Single-node multi-GPU capacity that is manually underutilized.

### 2.5 Explicit non-goals through v1

Cobra is not expected to solve the following before v1:

- Full semantic replacement of CPython.
- Automatic compilation of every package on PyPI.
- Automatic partitioning of an arbitrary single model across a cluster.
- A new tensor framework replacing PyTorch, JAX, or TensorFlow.
- A new dataframe implementation replacing pandas or cuDF.
- Automatically outperforming cuBLAS, cuDNN, or every specialized kernel.
- Multi-node fault-tolerant cluster scheduling in the core v1 release.
- Perfect static proof of purity for arbitrary dynamic Python.
- Transparent acceleration of code that performs frequent unknown mutation or external I/O.
- Windows and macOS production support before the Linux implementation is mature.

### 2.6 Product success metrics

Cobra succeeds only if it produces measurable economic value against strong baselines.

Primary metrics:

- End-to-end throughput.
- End-to-end p50, p95, and p99 latency.
- GPU-seconds per unit of useful work.
- CPU-seconds per unit of useful work.
- Peak and steady-state host and device memory.
- Host-to-device and device-to-host bytes transferred.
- GPU utilization and GPU idle gaps.
- Kernel launch count.
- Compile latency and time to break even.
- Correctness parity with eager execution.
- Percentage of execution captured, optimized, and safely parallelized.

Secondary metrics:

- Warm cache hit rate.
- Number of graph breaks.
- Recompilation rate.
- Number of runtime guard failures.
- Crash-free and wrong-code-free execution hours.
- Percentage of partner workloads that show a material improvement.

---

## 3. Product experience

### 3.1 Python API

The intended primary API is:

```python
import cobra_compiler as cobra

@cobra.compile(
    mode="inference",
    target="cuda",
    math="strict",
    fallback="eager",
)
def pipeline(data):
    x = preprocess(data)
    a = model_a(x)
    b = model_b(x)
    return merge(a, b)
```

Additional APIs:

```python
@cobra.pure
def normalize_metadata(metadata):
    ...

@cobra.effects(reads=["customer_table"], writes=[])
def lookup_customer(customer_id):
    ...

@cobra.task(device="cpu", estimated_cost="medium")
def custom_cpu_stage(x):
    ...
```

User annotations are assertions. In debug and shadow modes, Cobra should validate as much of the assertion as practical. A false purity or effect declaration must produce a clear warning and may be treated as undefined behavior only after the user explicitly enables a trust mode. The default mode remains conservative.

### 3.2 Command line interface

```bash
cobra run app.py
cobra run app.py --mode=inference --target=cuda
cobra compile module.py:pipeline --inputs examples/inputs.json
cobra explain module.py:pipeline
cobra benchmark module.py:pipeline --baseline=eager
cobra doctor
cobra cache list
cobra cache prune
cobra trace app.py --output trace.json
```

### 3.3 Execution modes

| Mode | Purpose | Behavior |
|---|---|---|
| `eager` | Diagnostic baseline | Runs without Cobra optimization. |
| `trace` | Capture analysis | Captures supported regions and prints breaks without compiling. |
| `auto` | Default production mode | Compiles profitable regions and falls back elsewhere. |
| `strict` | Correctness and CI | Fails when a requested region cannot be compiled or when semantics are uncertain. |
| `shadow` | Safe production evaluation | Runs eager and Cobra for sampled requests, compares outputs, reports divergence. |
| `aot` | Deployment | Produces a versioned artifact for a declared hardware and software target. |

### 3.4 Explainability output

`cobra explain` must produce both human-readable text and machine-readable JSON.

Example:

```text
Cobra plan for score_customers

Captured nodes:                  42
Python fallback nodes:            3
Parallel regions:                 2
Tensor regions:                   4
Relational regions:               1
Expected host-to-device copies:   1
Copies removed:                   3
CUDA graph candidates:            2

Placement
  parquet/filter/features    GPU 0 via cuDF
  model_a                    GPU 0 via TorchInductor
  model_b                    GPU 1 via TorchInductor
  combine                    GPU 0 via generated Triton kernel

Fallbacks
  custom_logger              unknown external side effect
  user_callback              unsupported dynamic Python object

Guards
  dataframe schema hash
  tensor dtype and rank
  model identity and parameter version
  CUDA device architecture
```

Every optimization report must identify:

- the original source span.
- the emitted graph nodes.
- the selected backend.
- the reason for placement.
- estimated and observed costs.
- guard conditions.
- fallback reason.
- expected transfer and synchronization behavior.

---

## 4. Technical positioning and build-versus-integrate decision

### 4.1 Relevant systems

Cobra should learn from and integrate with existing systems rather than rebuild their strongest components.

- **scriptc** demonstrates the value of compiling a familiar dynamic-language surface into native artifacts.
- **Bend and HVM** demonstrate a programming model where dependencies expose implicit parallelism, while also illustrating the difficulty of matching mature code generation.
- **Codon** provides an Apache-licensed high-performance Python-like compiler, native NumPy support, LLVM integration, and GPU capabilities.
- **PyTorch compile and export** provide graph capture, guards, graph breaks, custom backends, Inductor, and AOT deployment paths.
- **Triton** provides a productive and mature route for generated GPU kernels.
- **cuDF pandas acceleration** demonstrates zero-code-change dataframe acceleration with fallback.
- **MLIR** provides reusable dialect infrastructure for heterogeneous compilers.
- **CUDA Graphs** reduce repeated launch overhead for stable GPU workflows.
- **CUDA Tile** provides a higher-level NVIDIA-native kernel target that abstracts lower-level GPU details.
- **Arrow and DLPack** provide standardized low-copy and zero-copy interchange boundaries.

### 4.2 Recommended architecture decision

Cobra should be an independent compiler and runtime built on MLIR, CPython integration, and existing AI backends. It should not begin as a hard fork of Codon, PyTorch, Bend, or HVM.

Reasons:

1. Cobra's primary semantic contract is compatibility with ordinary CPython-hosted applications, including graceful fallback.
2. Cobra's differentiator is cross-library program capture and scheduling, not only scalar Python compilation.
3. A hard fork would couple Cobra's release cycle to another compiler's language semantics and internal architecture.
4. Existing systems can be integrated as backends or adapters without surrendering Cobra's global program graph.
5. The compiler must remain free to represent pandas, PyTorch, external tasks, effects, device placement, and runtime scheduling in one graph.

Codon remains useful as:

- a research reference.
- a possible future CPU scalar-region backend.
- an optional plugin for statically compilable functions.
- a source of implementation lessons for Python type specialization and native NumPy.

Bend and HVM remain useful as:

- conceptual references for dependency-derived parallelism.
- experimental backends for pure recursive tasks only if a measured workload justifies the integration.

They should not be used as the core runtime for tensor and dataframe operations.

### 4.3 Decision matrix

| Option | Time to prototype | CPython compatibility | Cross-library control | GPU path | Long-term risk | Decision |
|---|---:|---:|---:|---:|---:|---|
| Fork Codon | Medium | Medium | Medium | Medium | High coupling | Do not use as core. |
| Extend TorchDynamo only | Fast | High inside PyTorch regions | Low outside PyTorch | Strong | PyTorch-specific | Use as tensor adapter. |
| Build on Bend/HVM | Medium | Low | Medium | Experimental | Codegen maturity | Research only. |
| Custom CPython-hosted capture plus MLIR | Medium | High | High | Strong through adapters | Largest initial engineering load | Recommended. |
| Full new Python compiler | Slow | Low initially | High | Custom | Excessive scope | Explicitly defer. |

---

## 5. System architecture

### 5.1 High-level architecture

```text
                         Python application
                                |
                   Cobra frontend and adapters
                                |
               capture, guards, effects, graph breaks
                                |
                     Cobra Program Graph IR
                                |
         +----------------------+----------------------+
         |                      |                      |
    Tensor regions        Relational regions      Python/native tasks
         |                      |                      |
 PyTorch/Inductor       cuDF/Substrait/Arrow      CPython or LLVM
 Triton/CUDA Tile              |                      |
         +----------------------+----------------------+
                                |
                  Global optimizer and cost model
                                |
                   Memory and placement planner
                                |
                    Cobra Schedule IR and runtime
                                |
          +---------------------+----------------------+
          |                     |                      |
      CPU workers          CUDA streams          Multi-GPU/NCCL
```

### 5.2 Compiler pipeline

```text
Source and runtime values
        |
Capture frontend
        |
High-level Python and library graph
        |
Effect and alias analysis
        |
Shape, dtype, schema, and device inference
        |
Graph partitioning and graph-break insertion
        |
Domain-specific optimization
        |
Fusion and transfer elimination
        |
Placement and memory planning
        |
Schedule generation
        |
Backend compilation
        |
Guarded artifact cache
        |
Execution and telemetry feedback
```

### 5.3 Major subsystems

1. **Python capture frontend**
   - decorator and context manager.
   - lazy proxy objects.
   - import and adapter registry.
   - graph breaks and materialization.
   - runtime guard generation.

2. **Compiler core**
   - MLIR context and Cobra dialects.
   - effect and alias analyses.
   - partitioning, fusion, placement, and memory passes.
   - verifier and deterministic textual IR.

3. **Framework adapters**
   - PyTorch.
   - pandas and cuDF.
   - NumPy.
   - Arrow and DLPack.
   - plugin SDK for additional libraries.

4. **Backend layer**
   - TorchInductor and Triton.
   - CUDA libraries.
   - CUDA Tile.
   - LLVM CPU code generation.
   - external opaque task execution.

5. **Runtime**
   - task DAG executor.
   - CPU worker pool.
   - CUDA stream and event manager.
   - memory pools and buffer planner.
   - cancellation, exception, and fallback handling.
   - multi-GPU placement and NCCL collectives.

6. **Developer tooling**
   - explain report.
   - benchmark harness.
   - trace viewer.
   - cache inspection.
   - environment diagnostics.

---

## 6. Frontend and capture model

### 6.1 v0.1 capture strategy

The v0.1 frontend should use lazy capture rather than attempt a complete Python bytecode compiler.

Execution flow:

1. `@cobra.compile` enters a capture context.
2. Supported inputs are wrapped as Cobra proxy values containing metadata and optional concrete storage.
3. Calls recognized by adapters emit graph nodes instead of immediately executing.
4. Supported calls return proxy values.
5. Independent nodes remain lazy and can be scheduled concurrently.
6. A Python operation requiring a concrete value triggers materialization of the minimum necessary subgraph.
7. Unknown calls create a graph break and execute eagerly.
8. The resulting trace is specialized using runtime guards and cached.

This model provides immediate practical value without requiring Cobra to understand all Python semantics.

### 6.2 Capture levels

| Level | Description | v0.1 behavior |
|---|---|---|
| Function boundary | Decorated Python function | Required. |
| Library call | Known pandas, NumPy, or PyTorch call | Captured by adapter. |
| Tensor graph | PyTorch region | Delegated to PyTorch capture. |
| Relational chain | Supported dataframe operations | Captured into Cobra relational nodes. |
| Scalar Python | Typed arithmetic and loops | Eager in v0.1, native in later releases. |
| Unknown C extension | Opaque behavior | Graph break unless an adapter exists. |
| External I/O | File, network, database, logging | Explicit effectful task or graph break. |

### 6.3 Graph breaks

A graph break is a correctness boundary, not a failure.

Graph breaks occur when:

- an operation has unknown effects.
- a Python branch requires a concrete dynamic value.
- an unsupported object escapes into ordinary Python.
- a C extension cannot be observed through a supported adapter.
- a mutation cannot be modeled safely.
- a backend cannot compile a region.
- the planner predicts that compilation would not be profitable.

Every graph break must include:

- source location.
- reason code.
- suggested remediation if available.
- performance impact estimate.
- whether a plugin or annotation could remove the break.

### 6.4 Runtime guards

Compiled artifacts are valid only while their assumptions hold.

Guard classes:

- Python function and code object identity.
- model object identity.
- model parameter version or hash.
- tensor dtype, rank, shape constraints, strides, layout, and device.
- dataframe schema, dtypes, nullable behavior, and index assumptions.
- library and ABI versions.
- CUDA driver, runtime, architecture, and backend versions.
- effect annotation version.
- environment flags affecting semantics.
- math and determinism mode.

Guard policy:

1. Fast guards execute before dispatch.
2. A failed guard attempts a compatible cached specialization.
3. If none exists, Cobra recompiles within a configured budget.
4. Repeated specialization churn triggers eager fallback and a diagnostic.
5. The default maximum recompilations per region is configurable and must be conservative.

### 6.5 Fallback contract

Fallback must preserve observable Python behavior.

Cobra must never silently:

- skip an operation.
- reorder an unknown side effect.
- swallow or replace an exception.
- change a warning into silence.
- mutate an object differently.
- use relaxed floating-point behavior in strict mode.

Fallback overhead budgets:

- v0.1: no more than 5 percent median overhead for a fully unsupported function after warm-up.
- beta: no more than 3 percent.
- v1: no more than 2 percent.

---

## 7. Intermediate representation design

### 7.1 IR design principles

Cobra should use a small number of project-specific dialects and reuse standard MLIR dialects whenever their semantics are sufficient.

Principles:

- SSA values for data dependencies.
- explicit effect tokens for ordering constraints.
- explicit device and memory-space metadata.
- source provenance on every node.
- deterministic textual serialization.
- verifier-enforced invariants.
- versioned bytecode and cache metadata.
- progressive lowering from semantic to hardware-specific representations.

### 7.2 Recommended Cobra dialects

#### `cobra.program`

Represents the captured Python program at a task and library-call level.

Core operations:

- `cobra.program.region`
- `cobra.program.call`
- `cobra.program.fallback`
- `cobra.program.guard`
- `cobra.program.materialize`
- `cobra.program.effect_token`
- `cobra.program.fork`
- `cobra.program.join`
- `cobra.program.raise`
- `cobra.program.cancel`

#### `cobra.tensor`

Represents framework-independent tensor operations before lowering or delegation.

Core categories:

- elementwise operations.
- reductions.
- reshape, transpose, slice, concatenate, and broadcast.
- matrix multiplication and convolution markers.
- normalization and softmax markers.
- external compiled tensor region.
- tensor-to-tensor-framework interchange.

Cobra should not duplicate every ATen operation in v0.1. Unsupported or complex regions may remain an external compiled tensor call.

#### `cobra.rel`

Represents dataframe and relational operations.

Core operations:

- scan.
- project.
- filter.
- join.
- group and aggregate.
- sort.
- window.
- cast.
- null handling.
- materialize.
- dataframe-to-tensor conversion.

Where possible, Cobra should maintain a mapping to Substrait semantics for interchange and validation.

#### `cobra.schedule`

Represents the selected execution plan.

Core operations:

- task launch.
- device assignment.
- stream assignment.
- asynchronous copy.
- event record and wait.
- CUDA graph capture and replay.
- allocation and release.
- collective communication.
- fallback launch.

### 7.3 Standard MLIR dialects to reuse

- `func` for functions.
- `scf` and `cf` for structured and unstructured control flow.
- `async` for asynchronous dependencies.
- `arith`, `math`, and `complex` for scalar computation.
- `tensor` and `memref` for shaped data and buffers.
- `linalg` for structured tensor computations.
- `vector` for vectorization.
- `gpu` for generic GPU launches.
- `nvgpu` and `nvvm` for NVIDIA-specific lowering.
- `llvm` for CPU and low-level runtime lowering.
- `transform` for declarative tuning strategies where useful.

### 7.4 Effect SSA

Cobra should represent effects using explicit tokens.

Example:

```text
%t1, %df = cobra.program.call @read_parquet(%t0, %path)
  effects = [filesystem.read]

%features = cobra.rel.pipeline %df
  effects = [read(%df)]

%a = cobra.program.call @model_a(%features)
  effects = [read(%features), read(model_a.parameters)]

%b = cobra.program.call @model_b(%features)
  effects = [read(%features), read(model_b.parameters)]

%out = cobra.program.join %a, %b
```

The absence of a conflicting effect edge permits concurrent execution of `%a` and `%b`.

### 7.5 IR invariants

Every pass must preserve these invariants:

1. Data dependencies dominate all uses.
2. Conflicting effects remain ordered.
3. Unknown effects act as full barriers unless explicitly isolated.
4. Device transfers are explicit after placement lowering.
5. Values have a valid ownership and lifetime model.
6. Exceptions have a deterministic propagation policy.
7. Every lowered operation has a valid fallback or hard failure policy.
8. Source provenance survives all transformations.
9. Strict math mode does not introduce unapproved reassociation or precision loss.
10. The schedule cannot exceed declared resource and memory limits.

---

## 8. Effect, alias, and parallelism model

### 8.1 Effect lattice

Each operation may declare one or more effects:

- `pure`
- `read(alias_set)`
- `write(alias_set)`
- `mutate(alias_set)`
- `global_read(name)`
- `global_write(name)`
- `filesystem_read(path_class)`
- `filesystem_write(path_class)`
- `network_read(endpoint_class)`
- `network_write(endpoint_class)`
- `stdout`
- `warning`
- `random(state_id)`
- `device_state(device_id)`
- `synchronization(resource)`
- `unknown`

Parallelism is allowed only when:

- all data dependencies are satisfied.
- effect sets do not conflict.
- alias analysis proves no conflicting mutation.
- exception behavior can be preserved.
- estimated benefit exceeds scheduling and transfer overhead.
- resource and memory budgets permit concurrency.

### 8.2 Alias analysis

Cobra needs library-specific alias models.

For tensors:

- identify storage identity.
- distinguish views from copies.
- track strides and offsets.
- observe framework version counters when available.
- treat in-place operations as writes to the storage alias set.

For dataframes:

- distinguish logical plans from materialized mutable objects.
- model `inplace=True` and view-like behavior conservatively.
- treat unknown extension arrays as potential aliases.
- preserve pandas index and nullable semantics.

For ordinary Python objects:

- default to unknown aliasing.
- improve precision through immutable built-in types, dataclasses, frozen objects, and adapter metadata.

### 8.3 Exception semantics

Parallel execution may cause multiple tasks to fail concurrently. Cobra must preserve a deterministic approximation of Python source-order behavior.

Policy:

1. Every task receives a source-order index.
2. If several pure parallel tasks fail, Cobra reports the exception from the earliest source-order task.
3. Later task failures are attached as suppressed diagnostics in debug mode.
4. Effectful operations are not reordered across potentially throwing operations unless safety is proven.
5. Cancellation is best effort and must not hide a previously selected exception.
6. Resource failures such as device OOM are reported with the selected schedule and fallback attempts.

### 8.4 Randomness and determinism

Stateful random number generation is an effect.

Default strict behavior:

- preserve RNG state order.
- do not parallelize operations sharing a stateful generator.
- capture and restore framework RNG states during shadow comparisons.

Parallel RNG is allowed when:

- the API is stateless or key-based.
- independent generators are explicit.
- the user enables a reproducible partitioning policy.

Cobra exposes:

```text
--determinism=strict
--determinism=reproducible
--determinism=off
```

### 8.5 Parallel scheduling algorithm

Initial planner inputs for every node:

- candidate devices and backends.
- estimated compute cost by device.
- input and output sizes.
- transfer costs.
- memory demand and lifetime.
- effect and alias constraints.
- critical-path distance.
- compile cost.
- backend confidence.

Initial v0.1 planner:

1. Validate graph and effect constraints.
2. Fuse compatible adjacent nodes.
3. Estimate the critical path.
4. Remove placements that violate capability or memory constraints.
5. Assign nodes using earliest-finish-time scheduling with transfer cost.
6. Prioritize ready nodes by critical-path length and memory pressure.
7. Perform a bounded local search to reduce makespan and copies.
8. Emit a deterministic schedule.
9. Compare estimated gain against the strongest fallback plan.
10. Reject the optimization when the predicted gain is below the confidence threshold.

Pseudocode:

```text
for node in topological_order(graph):
    candidates = feasible_placements(node)
    for placement in candidates:
        start = max(
            device_available_time[placement.device],
            max(predecessor_finish + transfer_cost)
        )
        finish = start + estimated_compute_cost(node, placement)
        score = finish + memory_penalty + uncertainty_penalty
    choose lowest score

run bounded local search over adjacent placements
validate memory peak and effect order
emit schedule only if expected benefit > optimization threshold
```

### 8.6 Granularity control

Cobra must avoid creating thousands of tasks whose overhead exceeds useful work.

Mechanisms:

- measured per-machine task overhead calibration.
- minimum task cost threshold.
- fusion of small adjacent tasks.
- batching of repeated homogeneous tasks.
- coarsening of recursive or fine-grained graphs.
- maximum ready-queue depth.
- bounded number of CUDA streams.
- backpressure when memory or compilation queues are saturated.

Thresholds must be calibrated, not permanently hard-coded.

---

## 9. Tensor execution strategy

### 9.1 v0.1 principle

Cobra should not compete with PyTorch's tensor compiler inside regions PyTorch already optimizes well. Cobra should capture the program around those regions, preserve cross-region dependencies, and use PyTorch compilation as a backend.

### 9.2 PyTorch adapter

The adapter should support two capture paths:

1. **JIT path:** use the supported PyTorch compile backend interface for functions and modules encountered during normal execution.
2. **AOT path:** use exported model representations where the user requests a stable deployment artifact.

The adapter records:

- input and output tensor metadata.
- shape constraints and guards.
- mutation and alias behavior.
- model parameter identity and version.
- autograd requirements.
- backend compile artifact.
- expected workspace and memory use.

### 9.3 Tensor backend selection

| Operation class | Preferred v0.1 backend |
|---|---|
| Existing PyTorch graph | TorchInductor. |
| Matrix multiplication | Existing framework dispatch to cuBLAS or cuBLASLt. |
| Convolution | Existing framework dispatch to cuDNN. |
| Simple elementwise chain | Triton template or Inductor. |
| Reduction and normalization | Inductor or validated Triton template. |
| Custom unsupported op | Eager PyTorch or registered plugin. |
| Stable repeated region | Optional CUDA Graph capture. |

### 9.4 Generated kernels

Cobra-generated kernels should be limited to patterns with clear ownership and strong tests:

- pointwise fusion.
- simple reductions.
- normalization epilogues.
- layout conversions.
- dataframe-to-tensor packing.
- small postprocessing kernels.

Kernel generation order:

1. Reuse a vendor library if it is a natural match.
2. Reuse an existing framework kernel.
3. Use a validated Triton template.
4. Generate CUDA Tile code after beta qualification.
5. Use custom CUDA C++ only when other paths cannot express the operation or do not meet performance targets.

### 9.5 Math modes

```text
strict   Preserve documented framework behavior and conservative precision.
relaxed  Permit documented reassociation and reduced precision where output tolerance is satisfied.
fast     Permit aggressive fast-math transformations explicitly requested by the user.
```

Strict is the default.

Every optimization that changes numerical behavior must be:

- mode-gated.
- visible in `cobra explain`.
- tested against dtype-specific tolerances.
- benchmarked separately.

### 9.6 Training support

Training is not a v0.1 release requirement.

Beta training scope:

- capture a full training step as an opaque or partially decomposed region.
- preserve autograd and optimizer mutation order.
- support deterministic RNG policies.
- integrate existing PyTorch distributed primitives rather than replacing them.
- no automatic model sharding guarantee.

v1 training scope:

- supported training iterations may be captured across preprocessing, forward, backward, optimizer, and data movement.
- cross-step CUDA Graph capture may be used when shapes and memory addresses are stable.
- branch-level multi-GPU parallelism is supported where semantics are clear.

---

## 10. Dataframe and relational execution strategy

### 10.1 v0.1 supported operations

The first dataframe adapter should support a carefully tested subset:

- `read_parquet`.
- column projection.
- boolean filtering.
- supported scalar expressions.
- `assign` for supported expressions.
- `astype`.
- `fillna` and `dropna`.
- group-by with common aggregations.
- merge and join for supported key types.
- sort.
- conversion to Arrow, NumPy, or tensor.

Unsupported operations materialize and fall back to pandas.

### 10.2 Backend policy

- GPU-capable relational plans may execute through cuDF.
- CPU plans may execute through pandas initially.
- Beta may add an Arrow or Substrait-compatible native CPU engine.
- The planner chooses GPU only when compute savings exceed transfer and setup costs.
- Data already needed by a downstream GPU model receives an additional GPU-placement benefit.

### 10.3 Relational optimization

Supported optimizations:

- projection pruning.
- predicate pushdown.
- filter and projection fusion.
- column lifetime reduction.
- join strategy selection.
- aggregate partialization where supported.
- dataframe-to-tensor packing fusion.
- avoiding conversion through intermediate NumPy arrays.

### 10.4 Semantic hazards

Dataframe compatibility tests must explicitly cover:

- index preservation.
- duplicate columns and keys.
- nullable integer and boolean types.
- NaN versus null semantics.
- categorical values.
- time zones.
- stable sort behavior.
- string encodings.
- group-by null handling.
- join ordering.
- extension arrays.

Cobra must fall back rather than approximate unsupported pandas behavior.

---

## 11. Interoperability and memory model

### 11.1 Tensor interchange

DLPack is the preferred tensor exchange boundary.

Cobra must track:

- producer ownership.
- consumer borrowing.
- deleter and lifetime callback.
- device and stream synchronization.
- dtype, shape, and strides.
- read-only versus mutable access.

### 11.2 Columnar interchange

Apache Arrow C Data Interface is the preferred in-process columnar exchange boundary. The Arrow C Device interface should be used for device-resident columnar buffers when supported.

Cobra must avoid:

```text
pandas -> NumPy copy -> Torch CPU copy -> CUDA copy
```

Preferred path:

```text
Arrow or cuDF device buffers -> validated zero-copy or single-pack tensor -> model
```

### 11.3 Buffer ownership

Every runtime value must include:

- logical type.
- physical type.
- shape or schema.
- device and memory space.
- storage identity.
- owner.
- borrow count or lifetime token.
- mutation permission.
- last writer event.
- expected release point.

### 11.4 Memory planning

The planner computes value lifetimes and reuses compatible buffers when lifetimes do not overlap.

Features:

- host memory pool.
- pinned host memory pool.
- device memory pool per GPU.
- stream-aware release.
- workspace reservation.
- peak-memory prediction.
- buffer donation where semantics permit.
- memory pressure feedback to the scheduler.

### 11.5 OOM policy

On predicted or observed OOM:

1. reduce concurrency.
2. release compilation and temporary caches.
3. select a lower-workspace backend.
4. spill selected values to host if profitable and allowed.
5. retry a smaller schedule once.
6. fall back to eager execution if safe.
7. report the exact allocation, value, source span, and schedule decision.

Silent retry loops are forbidden.

---

## 12. Runtime architecture

### 12.1 Runtime components

- global DAG coordinator.
- CPU work-stealing pool.
- one submission coordinator per CUDA device.
- CUDA compute stream pool.
- dedicated copy streams.
- event pool.
- memory pools.
- compile and artifact cache.
- telemetry collector.
- cancellation and exception coordinator.

### 12.2 CPU execution

The CPU runtime should use native threads and release the GIL for native tasks.

Rules:

- ordinary Python fallback remains subject to the GIL.
- native CPU tasks execute in the C++ worker pool.
- CPU affinity is configurable.
- NUMA topology is detected and exposed to the planner.
- large dataframe and memory tasks should be NUMA-aware by beta.

### 12.3 CUDA execution

Each device owns:

- one default compute stream.
- a bounded pool of additional compute streams.
- one or more copy streams.
- event objects for cross-stream dependencies.
- a device memory pool.
- a backend capability registry.

The scheduler emits explicit event dependencies instead of global synchronization wherever possible.

### 12.4 CUDA Graphs

Stable repeated subgraphs may be captured when:

- memory addresses are stable or graph update semantics are supported.
- launch configurations are compatible.
- no unsupported external operation occurs inside the region.
- shape guards are satisfied.
- capture produces a measured benefit.

Cobra must report:

- capture eligibility.
- capture failures.
- replay count.
- launch-overhead savings.
- graph invalidation reason.

### 12.5 Multi-GPU execution

Beta scope:

- independent branch placement across GPUs.
- peer-to-peer copies where supported.
- explicit transfer and event coordination.
- simple replicated model placement.
- NCCL for required collectives.

v1 scope:

- topology-aware placement within one node.
- branch replication and load balancing.
- supported collective patterns.
- memory-aware assignment.
- deterministic failure handling.

Automatic tensor or pipeline model parallelism for an arbitrary single model remains post-v1 unless inherited from a backend such as PyTorch distributed.

### 12.6 Cancellation

Cancellation states:

- not started.
- submitted.
- running.
- completed.
- failed.
- cancellation requested.
- abandoned but draining.

CPU tasks may be cooperatively cancelled. GPU tasks already submitted generally cannot be forcibly removed, so the runtime must drain them safely while suppressing unused outputs.

### 12.7 Runtime ABI

Cobra should expose a stable C ABI for backend and framework plugins by v1.

The C ABI should cover:

- value descriptors.
- device descriptors.
- stream and event handles.
- task launch.
- memory allocation hooks.
- guard evaluation.
- telemetry callbacks.
- plugin version negotiation.

C++ APIs may evolve faster. The Python API remains the primary user surface.

---

## 13. Cost model and autotuning

### 13.1 Cost model inputs

- operation type.
- shape, schema, dtype, and layout.
- estimated FLOPs.
- estimated bytes read and written.
- transfer size and topology.
- backend launch overhead.
- measured machine calibration.
- device occupancy and memory pressure.
- compile cost.
- historical observations for equivalent signatures.
- uncertainty score.

### 13.2 Cost model stages

#### v0.1

- analytical estimates.
- lookup tables from machine calibration.
- deterministic heuristics.
- observed runtime correction.

#### Beta

- persistent per-hardware performance database.
- bounded candidate benchmarking.
- confidence intervals.
- topology-aware multi-GPU estimates.

#### v1

- optional learned cost model trained on local and fleet observations.
- deterministic fallback to analytical rules.
- explainable feature contribution report.
- strict privacy boundaries for enterprise telemetry.

### 13.3 Autotuning policy

Autotuning is bounded by:

- maximum compile time.
- maximum number of candidate executions.
- maximum memory use.
- production latency budget.
- user-selected mode.

Modes:

```text
off        No candidate benchmarking.
conservative  Small offline or first-run budget.
full       Larger explicit tuning run.
fleet      Enterprise service provides precomputed results.
```

Tuning results are content-addressed and hardware-specific.

### 13.4 Profitability gate

A compiled plan is installed only when:

```text
expected_runtime_gain
    > compile_amortization_penalty
    + scheduling_overhead
    + transfer_cost
    + uncertainty_margin
```

Cobra must report the estimated break-even number of executions.

---

## 14. Backends and code generation roadmap

### 14.1 v0.1 backend stack

- CPython eager fallback.
- PyTorch custom backend integration.
- TorchInductor for tensor graphs.
- Triton templates for selected fused kernels.
- cuDF for supported dataframe GPU execution.
- CUDA streams, events, and graphs.
- vendor libraries through existing frameworks.

### 14.2 Beta backend stack

- native MLIR lowering for typed scalar and simple NumPy regions.
- LLVM CPU code generation.
- broader generated Triton kernels.
- Substrait-compatible relational plan serialization.
- Arrow-native CPU execution experiments.
- multi-GPU scheduler and NCCL integration.
- experimental CUDA Tile backend.

### 14.3 v1 backend stack

- qualified CUDA Tile IR or CUDA Tile C++ path for supported kernels.
- Triton retained as a portable and mature fallback.
- AOT artifact packaging.
- stable CPU native region codegen.
- single-node multi-GPU schedule artifacts.
- plugin ABI for additional accelerators.

### 14.4 Post-v1 portability

The IR should permit future backends for:

- AMD ROCm.
- Intel GPUs.
- Apple accelerators.
- cloud-specific inference engines.
- IREE or other deployment runtimes.

No cross-vendor backend should be added before the CUDA implementation has compelling results and stable semantics.

---
## 15. Implementation languages and toolchain

### 15.1 Language choices

| Area | Primary language | Rationale |
|---|---|---|
| Compiler core | C++20 | Native MLIR and LLVM APIs, predictable performance, mature debugging and sanitizer support. |
| Cobra MLIR dialects and passes | C++20 plus TableGen | Standard MLIR implementation model, generated operation definitions, verifiers, parsers, and documentation. |
| Runtime and scheduler | C++20 | Low scheduling overhead, direct CUDA integration, deterministic resource management, and a stable C ABI. |
| Python capture frontend | Python 3 | Direct access to CPython, bytecode, framework APIs, user objects, and packaging ecosystem. |
| Framework adapters | Python first, C++ where required | Fast iteration at the boundary, native extensions only for hot or privileged paths. |
| Generated GPU kernels | Triton initially, CUDA Tile experimentally, vendor libraries where superior | Avoids rebuilding mature matrix and deep-learning kernels while retaining a path for custom fused kernels. |
| CPU code generation | MLIR to LLVM | Native scalar and array regions without creating a second compiler backend. |
| CLI | Python entry point over a native library | Fast product iteration with one authoritative native implementation. |
| Tests | C++, Python, MLIR test files, CUDA kernels | Test each layer using the most natural harness. |
| Documentation and examples | Markdown, MyST or Sphinx | Versioned, executable documentation with code validation. |

Rust is a reasonable future option for isolated services such as a remote cache or control plane, but it should not split the compiler and runtime implementation in the first release. The cost of two native ecosystems would exceed the safety benefit during the highest-change phase.

### 15.2 Required toolchain

The development environment should pin:

- a specific LLVM and MLIR commit or release branch.
- CMake and Ninja.
- Clang and LLD.
- Python build isolation through `uv`, `pip`, or an equivalent lock-capable workflow.
- PyTorch, Triton, pandas, NumPy, PyArrow, and RAPIDS versions.
- CUDA Toolkit, compatible NVIDIA driver floor, and NCCL for multi-GPU milestones.
- `ccache` or `sccache` for native builds.
- Docker or an OCI-compatible builder for reproducible CI images.
- Nsight Systems, Nsight Compute, and CUDA Compute Sanitizer in performance and correctness labs.

The repository must contain a machine-readable compatibility matrix. A release must never claim support for an untested combination merely because the package imports successfully.

Example:

```yaml
release: 0.1.0
platforms:
  - os: ubuntu-24.04
    arch: x86_64
    python: "3.12"
    pytorch: "pinned-minor"
    cuda_toolkit: "pinned-minor"
    driver_minimum: "documented-value"
    gpu_families:
      - ampere
      - hopper
```

Exact versions are selected and frozen at the start of each release train after compatibility testing.

### 15.3 Native ABI policy

Cobra should expose three layers:

1. A public Python API.
2. A stable C plugin ABI beginning at v1.
3. An internal C++ API with no compatibility guarantee.

The C ABI is used for:

- device backends.
- custom operation providers.
- memory allocators.
- telemetry sinks.
- cost-model plugins.
- enterprise scheduling policies.

C++ symbols must remain hidden by default. Public ABI structs must be versioned and size-tagged so newer runtimes can ignore unknown trailing fields.

---

## 16. Repository, build, and packaging design

### 16.1 Recommended repository layout

```text
cobra/
├── CMakeLists.txt
├── LICENSE
├── NOTICE
├── SECURITY.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── GOVERNANCE.md
├── THIRD_PARTY_NOTICES.md
├── pyproject.toml
├── uv.lock
├── cmake/
├── docs/
│   ├── architecture/
│   ├── decisions/
│   ├── guides/
│   ├── reference/
│   └── benchmarks/
├── include/cobra/
│   ├── c_api/
│   ├── runtime/
│   └── support/
├── lib/
│   ├── Analysis/
│   │   ├── AliasAnalysis/
│   │   ├── CostModel/
│   │   ├── DependencyAnalysis/
│   │   ├── EffectAnalysis/
│   │   └── ShapeAnalysis/
│   ├── Dialect/
│   │   ├── CobraProgram/
│   │   ├── CobraEffect/
│   │   ├── CobraTensor/
│   │   ├── CobraDataFrame/
│   │   ├── CobraPlacement/
│   │   └── CobraRuntime/
│   ├── Conversion/
│   │   ├── PythonToCobra/
│   │   ├── TorchToCobra/
│   │   ├── DataFrameToCobra/
│   │   ├── CobraToAsync/
│   │   ├── CobraToGPU/
│   │   ├── CobraToLLVM/
│   │   └── CobraToTriton/
│   ├── Optimizer/
│   ├── Planner/
│   ├── Runtime/
│   └── Support/
├── python/cobra_compiler/
│   ├── capture/
│   ├── adapters/
│   ├── backends/
│   ├── cli/
│   ├── diagnostics/
│   ├── testing/
│   └── _native/
├── runtime/
│   ├── core/
│   ├── cpu/
│   ├── cuda/
│   ├── dataframe/
│   └── distributed/
├── tools/
│   ├── cobra-opt/
│   ├── cobra-translate/
│   ├── cobra-runner/
│   ├── cobra-cache/
│   └── cobra-bench/
├── test/
│   ├── Analysis/
│   ├── Dialect/
│   ├── Conversion/
│   ├── Optimizer/
│   ├── Runtime/
│   ├── Integration/
│   ├── Differential/
│   ├── Fuzz/
│   ├── Packaging/
│   └── Security/
├── benchmarks/
│   ├── micro/
│   ├── tensor/
│   ├── dataframe/
│   ├── pipelines/
│   ├── baselines/
│   ├── harness/
│   └── reports/
├── examples/
├── docker/
├── scripts/
└── .github/workflows/
```

### 16.2 Build outputs

A standard build should produce:

```text
libcobra_runtime.so
libcobra_compiler.so
cobra-opt
cobra-translate
cobra-runner
cobra-bench
cobra_compiler/_native/*.so
```

Debug builds include assertions and full symbols. Release builds use hidden symbol visibility, link-time optimization where validated, and stripped distributable binaries with separate debug symbols.

### 16.3 Python packaging

The public project name is **Cobra**. Because the plain `cobra` package name is already associated with an established Python project, the recommended Python distribution name is:

```text
cobra-compiler
```

The import namespace should be explicit:

```python
import cobra_compiler as cobra
```

The CLI can still be:

```bash
cobra run app.py
```

The name must be reserved before a public announcement. A final trademark and package-name search is required before release.

Wheels should initially target:

- Linux x86_64.
- one documented glibc baseline.
- CPU-only frontend packages where possible.
- CUDA-specific runtime extras or separately versioned wheels if binary size and licensing require it.

Do not bundle unrestricted CUDA components by assumption. Every bundled NVIDIA library must appear in a redistribution manifest approved against the applicable toolkit license.

### 16.4 Reproducible builds

Every release must include:

- a pinned source revision.
- locked Python dependencies.
- pinned compiler container digest.
- generated SBOM in SPDX and CycloneDX formats.
- checksums for all artifacts.
- signed Git tag.
- provenance attestation.
- build instructions capable of reproducing the public artifacts within documented tolerances.

The release pipeline should produce artifacts from a clean, ephemeral environment. Developer laptops must never be a release authority.

---

## 17. Public product surface

### 17.1 Python API

The smallest coherent API is:

```python
import cobra_compiler as cobra

@cobra.compile(
    target="cuda",
    mode="safe",
    dynamic=True,
)
def pipeline(batch):
    features = preprocess(batch)
    left = model_a(features)
    right = model_b(features)
    return combine(left, right)
```

Additional surfaces:

```python
with cobra.capture(name="recommendation_pipeline"):
    result = pipeline(data)
```

```python
plan = cobra.explain(pipeline, sample_inputs=(data,))
print(plan.parallel_regions)
print(plan.device_transfers)
print(plan.graph_breaks)
```

```python
artifact = cobra.export(
    pipeline,
    sample_inputs=(data,),
    output="dist/pipeline.cobra",
)
```

### 17.2 CLI

```text
cobra run app.py
cobra build app.py --entrypoint module:function
cobra explain app.py --entrypoint module:function
cobra benchmark app.py --entrypoint module:function
cobra doctor
cobra cache list
cobra cache prune
cobra artifact inspect dist/pipeline.cobra
cobra replay trace.cobra-trace
```

`cobra explain` is a first-class product, not a debug afterthought. It must answer:

- Which regions were captured?
- Which regions fell back and why?
- Which values may alias?
- Which operations have side effects?
- Which branches may run concurrently?
- Which device was selected for each node?
- Which data transfers remain?
- Which kernels or vendor libraries were chosen?
- What assumptions and guards protect the plan?
- What is the estimated compilation break-even point?

### 17.3 Configuration

Configuration precedence:

```text
explicit API arguments
    > command-line flags
    > project cobra.toml
    > environment variables
    > system defaults
```

Example:

```toml
[project]
mode = "safe"
math = "strict"
fallback = "allow"
telemetry = "off"

[target]
backend = "cuda"
minimum_compute_capability = "project-pinned"

[optimizer]
auto_parallel = true
auto_placement = true
cuda_graphs = true
autotune = "conservative"

[cache]
directory = ".cobra/cache"
max_size_gb = 20

[diagnostics]
explain = "summary"
trace = false
```

### 17.4 Compilation modes

| Mode | Behavior |
|---|---|
| `safe` | Conservative effects, strict math, deterministic observable behavior, fallback allowed. Default. |
| `performance` | More aggressive placement, bounded autotuning, strict math unless separately changed. |
| `deterministic` | Stable schedules and framework deterministic settings where supported. |
| `debug` | Assertions, IR dumps, guard logs, scheduler trace, synchronous CUDA error checks. |
| `shadow` | Executes Cobra and reference paths, compares outputs, returns the reference result. |
| `aot` | No runtime tracing beyond declared dynamic guards. Produces a deployment artifact. |

Fast-math must be an independent, explicit option. It must never be implied by `performance`.

### 17.5 Artifact format

A `.cobra` artifact is a versioned container containing:

```text
manifest.json
program.mlirbc
execution-plan.pb or equivalent
kernels/
constants/
guards/
debug-map/
licenses/
sbom/
signatures/
```

The manifest records:

- Cobra compiler and runtime versions.
- source fingerprint.
- dependency fingerprints.
- Python and framework versions.
- target GPU family and minimum driver constraints.
- enabled semantic modes.
- expected input signature and dynamic dimensions.
- included kernels and required external libraries.
- artifact format version.

Artifacts must fail closed when an ABI, driver, architecture, or semantic requirement is incompatible.

### 17.6 Cache keys

A compilation cache key includes at least:

```text
source and bytecode fingerprint
captured constants
input type, shape, stride, dtype, device, and alias guards
framework adapter versions
Cobra compiler revision
backend revision
GPU architecture
semantic flags
cost-model version
autotuning result version
```

Cache entries must be integrity-checked. Remote cache entries are untrusted input and require signature or digest validation before loading native code.

---

## 18. TDD operating model

### 18.1 Core rule

No optimization exists until it has all of the following:

1. A written semantic contract.
2. A failing correctness test.
3. A minimal implementation that makes the test pass.
4. A differential test against the reference execution.
5. An IR regression test proving the intended transformation.
6. A benchmark hypothesis.
7. A benchmark that can disprove the hypothesis.
8. A fallback or disable mechanism.
9. User-facing diagnostics.

For compiler work, TDD is not only Red, Green, Refactor. Cobra uses:

```text
Specify
  -> Red
  -> Green
  -> Differential proof
  -> Performance proof
  -> Refactor
  -> Long-run validation
```

### 18.2 Feature development template

Every feature begins with a design issue containing:

```text
Problem
Semantic contract
Supported inputs
Explicitly unsupported inputs
Observable behavior
Effects and alias assumptions
Failure behavior
Fallback behavior
Expected IR before and after
Correctness oracle
Benchmark workload
Expected performance mechanism
Removal or rollback plan
```

Example for parallel branch execution:

```text
Claim:
Two captured calls with disjoint writes, shared read-only inputs,
no ordered effects, and independent exceptions may overlap.

Reference behavior:
Outputs and exceptions match sequential Python semantics.

Performance hypothesis:
On a GPU with available concurrent execution capacity,
overlap reduces critical-path latency by at least 10 percent.

Rollback:
Disable with cobra.optimizer.auto_parallel = false.
```

### 18.3 Pull request requirements

A compiler or runtime pull request is mergeable only when it includes the relevant subset of:

- C++ unit tests.
- Python unit tests.
- MLIR `lit` and `FileCheck` regression tests.
- differential tests against eager execution.
- property-based tests.
- a microbenchmark.
- an end-to-end benchmark result or an explanation of why no performance change is expected.
- diagnostics snapshot updates.
- documentation.
- release note fragment.

Generated IR changes require reviewer-visible before and after output.

### 18.4 Spike policy

Research spikes may bypass normal architecture requirements only on an isolated branch or under `experimental/`. No spike code enters a release path until it is:

- rewritten or hardened.
- covered by semantic and regression tests.
- placed behind a feature flag.
- measured against a baseline.
- reviewed for resource and security failure modes.

### 18.5 Wrong-code policy

A compiler that is fast and wrong is defective, not experimental.

Rules:

- Known silent wrong-code is release-blocking at every stage.
- A suspected wrong-code report disables the affected optimization by default until triaged.
- Every fixed wrong-code bug receives a minimized regression test.
- Security-sensitive or data-corrupting bugs receive an advisory process.
- Unsupported behavior must graph-break, fall back, or fail explicitly.

### 18.6 Benchmark-driven development without benchmark gaming

Each optimization must state the mechanism it expects to improve:

- fewer host-to-device transfers.
- fewer kernel launches.
- greater overlap.
- less allocation.
- better fusion.
- improved library dispatch.
- lower Python dispatch overhead.

The team must not accept speedups with no understood mechanism. Unexplained speedups frequently hide asynchronous timing mistakes, changed numerical semantics, or missing work.

---

## 19. Complete test strategy

### 19.1 Test pyramid

```text
                    Partner workloads
               End-to-end pipeline tests
             Differential and shadow tests
          Framework and backend integration tests
       Property, metamorphic, and fuzz testing
    Pass, dialect, scheduler, and runtime unit tests
```

Correctness gates run before performance gates. A benchmark result is invalid if its output has not passed the configured correctness oracle.

### 19.2 C++ unit tests

Use GoogleTest or an equivalent native framework for:

- graph construction.
- topological ordering.
- effect set operations.
- alias set merging.
- dominance and liveness helpers.
- cost arithmetic and uncertainty propagation.
- memory planner interval logic.
- scheduler readiness queues.
- event lifecycle.
- cache-key generation.
- artifact validation.
- error and cancellation propagation.

Tests must cover invalid inputs and resource exhaustion, not only the happy path.

### 19.3 Python unit tests

Use `pytest` for:

- decorators and context managers.
- bytecode and callable fingerprinting.
- proxy behavior.
- adapter registration.
- graph-break diagnostics.
- configuration precedence.
- cache behavior.
- CLI behavior.
- error messages.
- framework interoperability.
- pickling and multiprocessing boundaries where supported.

### 19.4 MLIR dialect and pass tests

Use LLVM `lit` and `FileCheck` for:

- parser and printer round trips.
- operation verification.
- canonicalization.
- constant folding.
- shape propagation.
- effect inference.
- dependency edge generation.
- alias-aware scheduling constraints.
- fusion legality.
- transfer elimination.
- device placement.
- CUDA Graph region formation.
- lowering to async, GPU, LLVM, Triton, or CUDA Tile paths.
- diagnostic quality for rejected IR.

Each pass gets both positive and negative tests. Negative tests prove that the optimizer does not transform an unsafe case.

### 19.5 Differential testing

For every supported construct, run:

```text
reference CPython and framework execution
versus
Cobra execution
```

Compare:

- return values.
- mutations visible to the caller.
- exception type and message class.
- exception ordering where observable.
- warning categories where part of the contract.
- stdout and stderr only for explicitly supported ordered I/O regions.
- random results under deterministic mode.
- dataframe schema, index, nulls, category metadata, and ordering.
- tensor shape, dtype, stride where promised, device, and values.

Use exact comparison for integers, booleans, strings, categorical metadata, and strict dataframe semantics. Floating-point tolerances must be operation and dtype specific, not a single global tolerance.

### 19.6 Property-based testing

Use Hypothesis or an equivalent generator for:

- tensor shapes, including zero dimensions.
- dynamic dimensions.
- contiguous and non-contiguous strides.
- sliced and transposed tensors.
- dtype combinations.
- NaN, infinity, signed zero, denormals, and extreme values.
- shared storage and view aliasing.
- nullable dataframe columns.
- duplicate keys.
- empty groups.
- timezone-aware timestamps.
- categorical columns.
- unusual Unicode strings.
- nested control flow.
- random dependency DAGs.
- randomized memory limits and scheduling delays.

A property-based failure must automatically persist its minimized reproducer as a normal regression fixture.

### 19.7 Metamorphic testing

Useful metamorphic relations include:

- adding a no-op must not alter outputs.
- changing independent source order must not alter a pure result.
- splitting a batch and concatenating results must match whole-batch execution for declared batch-independent operations.
- CPU and GPU execution must agree within the operation-specific numerical contract.
- enabling capture without optimizations must match eager behavior.
- serial and parallel scheduler modes must agree.
- cache miss and cache hit executions must agree.
- AOT and JIT artifacts must agree for the same guards.

### 19.8 Fuzz testing

Native fuzz targets should use libFuzzer or an equivalent engine for:

- MLIR parsers and bytecode readers.
- `.cobra` artifact manifests.
- cache metadata.
- shape expressions.
- guard evaluators.
- dependency graph construction.
- scheduler event sequences.
- plugin ABI input validation.
- remote cache responses.

Python-side structured fuzzing should generate:

- supported Python AST and bytecode fragments.
- combinations of tensor and dataframe calls.
- graph-break boundaries.
- exception paths.
- object mutation patterns.

Fuzz infrastructure must support deterministic replay from a seed and retain every crash corpus entry.

### 19.9 Tensor correctness matrix

Every supported tensor operation must be tested across a declared subset of:

| Dimension | Required cases |
|---|---|
| Dtype | bool, integer types, fp16, bf16, fp32, fp64 where supported. |
| Shape | scalar, empty, singleton, small, odd, power-of-two, large, dynamic. |
| Layout | contiguous, transposed, sliced, broadcast, strided. |
| Values | zeros, random, extremes, NaN, infinity, signed zero. |
| Device | CPU reference, one CUDA device, multiple CUDA devices when supported. |
| Gradients | no-grad, requires-grad, forward and backward once training enters scope. |
| Aliasing | independent, shared input, views, output alias where the framework permits it. |

Special attention is required for reductions, softmax, normalization, indexing, scatter and gather, random operations, and atomic accumulation because they are frequent sources of numerical or ordering divergence.

### 19.10 Dataframe correctness matrix

Each supported relational operation is tested for:

- empty frames.
- empty columns.
- nullable values.
- mixed null representations.
- duplicate column names where allowed.
- duplicate indexes.
- stable and unstable ordering contracts.
- joins with duplicate keys.
- outer joins and null keys.
- groupby with empty groups.
- categorical data.
- strings and Unicode.
- timezone-aware and naive timestamps.
- decimal and large integer behavior.
- schema changes.
- index preservation.
- pandas fallback boundaries.

The test oracle must include both values and metadata. A dataframe with correct numbers and a wrong index is wrong.

### 19.11 Effect and alias tests

Required cases:

- independent pure functions become parallel candidates.
- read and read may overlap.
- read and write to the same alias set may not overlap.
- write and write may not overlap unless the operation has an explicit commutative reduction contract.
- a view aliases its base allocation.
- uncertain aliases serialize in safe mode.
- file I/O remains ordered.
- logging and printing remain ordered unless explicitly isolated.
- global mutation remains ordered.
- random number generation follows the declared mode.
- exceptions preserve the selected Python semantic contract.
- cancellation does not expose partially committed state.

### 19.12 Scheduler tests

The scheduler requires deterministic simulation tests with a virtual clock and fake devices. Cases include:

- one chain.
- a wide fan-out and fan-in.
- mixed CPU and GPU nodes.
- transfer overlap.
- memory-pressure backoff.
- resource starvation.
- failed node propagation.
- cancellation.
- timeout.
- stream exhaustion.
- device loss.
- OOM retry policy.
- deterministic schedule mode.
- priority inversion prevention.
- multi-GPU placement.
- NCCL collective ordering.

The virtual scheduler is used for exhaustive small-DAG exploration. Real hardware tests then validate timing and CUDA behavior.

### 19.13 Memory safety and concurrency tests

Native CI and scheduled labs run:

- AddressSanitizer.
- UndefinedBehaviorSanitizer.
- ThreadSanitizer on CPU concurrency paths.
- LeakSanitizer where compatible.
- CUDA Compute Sanitizer `memcheck`.
- CUDA Compute Sanitizer `racecheck`.
- CUDA Compute Sanitizer `synccheck`.
- CUDA Compute Sanitizer `initcheck`.

GPU checks may run in dedicated nightly lanes because of execution cost. Release candidates must pass the complete matrix.

### 19.14 Failure injection

Introduce deterministic failure points for:

- allocation failure.
- CUDA allocation failure.
- kernel launch failure.
- device synchronization failure.
- corrupt cache entry.
- incompatible artifact.
- remote cache timeout.
- plugin crash or rejection.
- disk full.
- canceled user request.
- dataframe fallback failure.
- NCCL error in beta and v1.

The runtime must release resources, surface a useful error, and avoid returning partially valid output.

### 19.15 Integration matrix

At minimum, integration CI must cover:

```text
Python versions in the release support matrix
PyTorch versions in the release support matrix
pandas and NumPy pinned support versions
PyArrow and RAPIDS pinned support versions
CUDA and driver combinations in the support matrix
GPU families represented by physical test machines
Debug and release native builds
Capture enabled and disabled
Cold cache and warm cache
Strict and deterministic modes
```

Combinatorial explosion is controlled through pairwise testing on pull requests and full supported combinations on nightly or release lanes.

### 19.16 Packaging tests

For each wheel or container:

- install into a clean environment.
- run `cobra doctor`.
- compile and execute a smoke pipeline.
- verify fallback when no supported GPU is present.
- verify no undeclared host-library dependency.
- inspect wheel contents and licenses.
- scan for forbidden bundled CUDA libraries.
- validate artifact signatures and SBOM.
- uninstall cleanly.

### 19.17 Documentation tests

Every public code example is executable in CI. API snippets are type-checked where applicable. CLI help and documentation flags are compared to generated command definitions to prevent drift.

### 19.18 Security tests

Required cases include:

- malicious artifact path traversal.
- oversized or recursive manifests.
- malformed MLIR bytecode.
- poisoned remote cache objects.
- arbitrary library loading attempts.
- plugin ABI version confusion.
- cache key collision attempts.
- unsafe temporary-file handling.
- symlink attacks in local cache directories.
- command injection through compiler flags.
- secrets accidentally captured as constants.

Native code generation and loading must be treated as a security boundary even when the first deployment model is local.

### 19.19 Long-running tests

Run soak tests that repeatedly compile and execute representative pipelines while tracking:

- host memory.
- device memory.
- file descriptors.
- CUDA events and streams.
- cache growth.
- compilation latency drift.
- output divergence.
- scheduler queue depth.

A monotonic leak or unbounded cache is release-blocking.

---

## 20. Benchmark program

### 20.1 Benchmark principles

Cobra benchmarks must be:

- reproducible.
- statistically analyzed.
- correctness-gated.
- transparent about cold and warm execution.
- compared to credible alternatives.
- representative of cross-library AI workloads.
- resistant to cherry-picking.

The project should publish raw measurements and machine configuration, not only summary charts.

### 20.2 Required baselines

Every relevant benchmark compares four configurations:

| ID | Configuration |
|---|---|
| B0 | Ordinary eager CPython with the workload's normal pandas, NumPy, and PyTorch stack. |
| B1 | Strongest reasonable composition of existing automatic tools, such as `torch.compile` plus `cudf.pandas`, without hand-written application restructuring. |
| B2 | Hand-optimized reference using explicit CUDA streams, optimized transfers, framework compilation, or native libraries where practical. |
| B3 | Cobra using the release-default safe configuration. |

B1 is the most important product baseline. Beating unoptimized eager Python alone does not establish Cobra's unique value.

B2 estimates headroom. Cobra does not need to beat expert hand-tuned code in every case, but the gap must be measured.

### 20.3 Benchmark suites

#### A. Compiler and runtime microbenchmarks

Measure:

- callable capture latency.
- graph-node creation.
- guard evaluation.
- cache lookup.
- artifact loading.
- scheduler enqueue and dispatch.
- dependency resolution.
- CUDA event creation and reuse.
- memory-pool allocation and reuse.
- host-to-device and device-to-host transfer planning.
- CUDA Graph capture and replay.
- plugin dispatch.
- exception and cancellation propagation.

Use Google Benchmark for native components and `pyperf` for Python-facing components.

#### B. Tensor benchmarks

Include:

- elementwise chains.
- reductions.
- normalization.
- softmax.
- matrix multiplication dispatch.
- convolution dispatch.
- gather and scatter.
- mixed precision.
- dynamic shapes.
- non-contiguous inputs.
- two independent model branches.
- small-kernel launch-bound workloads.

Use a documented subset of TorchBench and additional Cobra-specific graph patterns. Do not claim broad framework speedup from a small hand-selected subset.

#### C. Dataframe benchmarks

Include:

- Parquet scan.
- filter and projection.
- groupby and aggregation.
- joins of different cardinalities.
- sort and window operations.
- string processing.
- null-heavy data.
- categorical data.
- dataframe-to-tensor conversion.
- fallback-heavy mixed queries.

Scale datasets through sizes that are CPU-favorable, transfer-bound, GPU-favorable, and memory-constrained.

#### D. End-to-end Cobra pipeline suite

The initial suite should contain at least these workloads:

1. `parquet_feature_inference`: Parquet scan, feature filtering, tensor conversion, model inference, result projection.
2. `tabular_recommender`: joins, categorical transforms, embeddings, ranking model, top-k output.
3. `multimodal_fanout`: shared preprocessing followed by independent vision and text branches, then fusion.
4. `model_ensemble`: one batch sent to several independent models, then weighted aggregation.
5. `batch_embeddings`: text preparation, variable-length batching, embedding model, normalization, persistence.
6. `rag_ingest`: document batches, parsing metadata, chunking, embedding, deduplication, and vector-write preparation.
7. `fraud_rules_model`: dataframe rules and feature engineering feeding a model, with ordered audit output outside the optimized region.
8. `cv_preprocess_inference_postprocess`: decode or prepared image input, tensor transforms, inference, non-maximum suppression or analogous postprocessing.
9. `llm_rerank`: candidate dataframe preparation, parallel scoring branches, merge, and top-k selection.
10. `training_step`: introduced in beta, covering data preparation, forward, backward, optimizer, and validation of gradient semantics.

Each benchmark must have:

- a frozen dataset generator or versioned dataset.
- a correctness oracle.
- an eager implementation.
- a strongest composed automatic baseline.
- a hand-tuned reference when affordable.
- expected bottleneck classification.
- target hardware profile.
- documented unsupported features.

### 20.4 Metrics

Record at least:

#### User-facing performance

- cold-start latency.
- first compiled execution latency.
- warm p50, p95, and p99 latency.
- throughput.
- time to break even after compilation.

#### Compute efficiency

- GPU-seconds per unit of work.
- CPU-seconds per unit of work.
- GPU active time.
- GPU utilization, interpreted with profiler evidence rather than as a standalone truth.
- achieved occupancy where relevant.
- SM and Tensor Core utilization where relevant.

#### Memory and data movement

- peak host memory.
- peak device memory.
- total host-to-device bytes.
- total device-to-host bytes.
- allocation count.
- memory-pool reuse.
- intermediate bytes materialized.

#### Execution structure

- Python graph breaks.
- captured statements or operations.
- number of scheduled tasks.
- number of parallel regions.
- kernel launches.
- generated kernels.
- vendor-library calls.
- CUDA Graph captures and replays.
- synchronization count.

#### Compilation

- capture time.
- analysis time.
- optimization time.
- code generation time.
- autotuning time.
- artifact size.
- cache hit ratio.

#### Reliability

- output mismatch count.
- fallback rate.
- recompilation count.
- guard failure rate.
- OOM count.

Energy may be reported as an experimental metric when the measurement setup is calibrated and documented.

### 20.5 Timing protocol

Rules:

1. Validate output before accepting a timing sample.
2. Separate cold compile, cold artifact load, and warm execution.
3. Synchronize CUDA correctly around wall-clock measurements.
4. Use CUDA events for GPU-region timing and wall clock for user-visible latency.
5. Include data transfer and required synchronization in end-to-end timing.
6. Do not include dataset generation unless it is part of the production workload.
7. Use warm-up runs until a documented stability criterion is met.
8. Collect at least 30 independent end-to-end samples unless the workload duration justifies a statistically equivalent protocol.
9. Randomize configuration order to reduce thermal and temporal bias.
10. Record every sample, including outliers. Exclusion requires a documented machine-level reason.

### 20.6 Machine control

Dedicated benchmark hosts should:

- disable unrelated workloads.
- pin CPU affinity where applicable.
- document CPU governor and frequency behavior.
- document GPU clocks, power limits, MIG configuration, and persistence mode.
- monitor temperature and throttling.
- use local data unless network I/O is explicitly under test.
- pin container, driver, toolkit, and library versions.
- reboot or reset the environment under a documented policy for long experiments.

Benchmark results from shared CI runners may catch coarse regressions but cannot serve as release performance evidence.

### 20.7 Statistical analysis

Report:

- median.
- p95 and p99 for service-like workloads.
- geometric mean speedup across a suite.
- bootstrap 95 percent confidence intervals.
- coefficient of variation or another noise indicator.
- absolute time as well as ratio.

A speedup claim is accepted only when:

- the confidence interval excludes no improvement at the selected threshold.
- the correctness oracle passes.
- profiling confirms the claimed mechanism.
- the same configuration is used across baselines except for the optimization under test.

### 20.8 Compilation amortization

For JIT paths, publish:

```text
break_even_runs = compile_time / (baseline_time - optimized_time)
```

When the denominator is zero or negative, Cobra must not recommend installation of that plan.

For variable workloads, compute break-even using expected traffic distribution, not only one ideal input.

### 20.9 Regression thresholds

Default policy:

| Lane | Alert | Block |
|---|---:|---:|
| Pull request microbenchmarks | greater than 5 percent regression with stable signal | greater than 10 percent or unexplained critical-path regression |
| Nightly suite | greater than 3 percent geometric-mean regression | greater than 5 percent geometric mean or greater than 10 percent on a release-critical workload |
| Release candidate | any unexplained greater than 3 percent regression | greater than 5 percent geometric mean or any greater than 10 percent critical workload regression |

Thresholds should be calibrated per benchmark noise. An absolute latency budget can override percentage thresholds for very small operations.

### 20.10 Benchmark publication

Every milestone report includes:

- Git revisions.
- artifact hashes.
- machine specifications.
- driver and software matrix.
- raw JSON or Parquet measurements.
- analysis notebook or script.
- known limitations.
- failed or regressed workloads.
- number of unsupported workloads.

A public dashboard should display regressions and unsupported cases, not only wins.

---

## 21. Continuous integration and release engineering

### 21.1 CI lanes

#### Pull request: CPU fast lane

Target duration should remain suitable for normal development. It runs:

- formatting and linting.
- Python type checking.
- C++ compile checks.
- unit tests.
- MLIR pass tests.
- selected property tests.
- packaging smoke test.
- documentation examples.
- changed-component microbenchmarks.

#### Pull request: GPU correctness lane

Runs on a representative GPU:

- CUDA runtime tests.
- selected differential tests.
- framework integration smoke tests.
- CUDA Graph tests.
- generated-kernel correctness.
- one small pipeline benchmark for gross regression detection.

#### Nightly lane

Runs:

- broader version matrix.
- complete differential suite.
- thousands of property cases per family.
- fuzz campaigns.
- sanitizers.
- full benchmark suite on controlled machines.
- leak and soak tests.
- artifact compatibility tests.

#### Weekly hardware matrix

Runs on each supported GPU family and all release-supported software combinations.

#### Release candidate lane

Runs the complete qualification matrix from clean source and produces the candidate artifacts that are later promoted without rebuilding.

### 21.2 Merge queue

Use a merge queue so the tested commit is the commit that lands. Performance-sensitive changes should serialize through controlled benchmark hosts to avoid conflicting measurements.

### 21.3 Branching and versioning

Use trunk-based development with short-lived feature branches. Maintain release branches only for supported patch lines.

Versioning:

```text
0.x: APIs and artifact format may change with migration notes.
1.x: public Python API and declared C plugin ABI follow semantic versioning.
artifact format: independently versioned with explicit compatibility range.
IR bytecode: internal unless explicitly promoted as a compatibility surface.
```

### 21.4 Feature flags

Every substantial optimizer pass and backend must have:

- a global feature flag.
- a per-region disable path where practical.
- a diagnostic identifier.
- telemetry counters when telemetry is enabled.
- a safe fallback.

This allows rapid mitigation without removing the complete compiler.

### 21.5 Release train

A release candidate progresses through:

```text
internal dogfood
  -> benchmark qualification
  -> design-partner shadow mode
  -> design-partner canary
  -> public release candidate
  -> signed general release
```

No candidate is rebuilt between final qualification and release. Promotion changes metadata, not binary content.

### 21.6 Compatibility policy

Each release publishes:

- tested combinations.
- minimum driver requirement.
- known incompatible combinations.
- deprecated API list.
- artifact compatibility range.
- fallback behavior for unsupported configurations.

A deprecation must normally survive at least one minor release during beta and two minor releases after v1, except for security or correctness emergencies.

---

## 22. Security, privacy, and supply-chain design

### 22.1 Threat model

Cobra handles and can generate executable code. Threats include:

- malicious source programs.
- compromised dependencies.
- poisoned local or remote caches.
- malicious `.cobra` artifacts.
- untrusted plugins.
- exposed model constants or secrets.
- unsafe native kernel generation.
- privilege escalation through compiler subprocesses.
- telemetry leakage.

The project must document which deployment models execute trusted code and which accept untrusted artifacts.

### 22.2 Process isolation

Compilation should support a sandboxed worker process with:

- no network access by default.
- restricted filesystem access.
- explicit temporary directories.
- resource limits.
- process timeout.
- controlled environment variables.
- a narrow IPC protocol.

Loading arbitrary Python modules is inherently code execution. Cobra must not advertise Python source compilation as a secure sandbox.

### 22.3 Artifact trust

A production runtime should support policies:

```text
allow unsigned local artifacts
require signature from trusted publisher
require exact source digest
forbid JIT compilation
forbid external plugins
```

Native blobs are validated before mapping. Manifests use bounded parsers and explicit size limits.

### 22.4 Secrets and constants

Capture may accidentally freeze:

- API keys.
- credentials.
- tokens.
- customer data.
- model prompts.
- filesystem paths.

The frontend must:

- classify captured constants.
- redact suspicious values from diagnostics.
- warn about large or secret-like constants.
- allow `cobra.dynamic()` to prevent constant capture.
- support an artifact inspection command.
- encrypt enterprise remote-cache traffic and storage.

### 22.5 Telemetry

Community Cobra defaults to telemetry off.

When enabled, collection must be explicit and documented. Default payloads should contain only technical counters such as:

- Cobra version.
- backend and hardware class.
- graph-break reason identifiers.
- compile and execution durations.
- feature usage.
- anonymized failure signatures.

Never collect source code, dataframe contents, tensor contents, model weights, paths, prompts, or captured constants by default.

### 22.6 Dependency and supply-chain controls

Required controls:

- dependency lock files.
- automated vulnerability scanning.
- license scanning.
- SBOM generation.
- signed commits or tags for release authority.
- protected release environments.
- two-person approval for release publication.
- artifact provenance.
- reproducible build checks.
- third-party notices.

### 22.7 Vulnerability response

Publish `SECURITY.md` with a private reporting channel and response policy. Severity triage must distinguish:

- remote or local code execution.
- artifact or cache poisoning.
- silent data corruption.
- information disclosure.
- denial of service.
- performance-only defects.

Silent wrong-code with security, financial, or scientific impact may require a security advisory even when there is no memory-safety exploit.

---
## 23. End-to-end engineering roadmap

The schedule below assumes a focused team of 8 to 10 engineers with regular access to controlled NVIDIA systems. Calendar estimates are planning ranges, not promises. With four engineers, scope must be reduced or elapsed time will likely approach twice the stated range.

### Phase 0: Thesis validation and semantic charter

**Duration:** Engineering weeks 1 through 4

**Goals:**

- Prove that Cobra can add value beyond `torch.compile` and `cudf.pandas` composed manually.
- Freeze the semantic principles that protect Python behavior.
- Establish benchmark infrastructure before building a large compiler.
- Kill weak architectural assumptions cheaply.

**Workstreams:**

1. Implement a disposable capture prototype that records calls, tensors, dataframe boundaries, dependencies, and timings.
2. Build three representative pipelines:
   - dataframe to tensor to model.
   - two independent model branches.
   - mixed CPU preprocessing and GPU inference.
3. Create B0, B1, B2, and prototype B3 baselines.
4. Measure copies, synchronization, kernel launches, GPU idle gaps, and overlap opportunities.
5. Write the semantic charter for effects, exceptions, random state, mutation, aliasing, and fallback.
6. Produce architectural decision records for MLIR, PyTorch integration, cuDF integration, and the runtime boundary.

**Exit criteria:**

- At least one cross-library pipeline shows a statistically valid improvement of 15 percent or more over B1, or a credible profiler-backed route to that result.
- The prototype identifies at least two optimization opportunities unavailable to a tensor-only compiler.
- No semantic mismatch in the curated prototype corpus.
- The team can explain every measured speedup through a profiler trace.
- A go, narrow, or stop decision is recorded.

If this gate fails, do not build a general compiler. Narrow the product to the strongest demonstrated layer, such as pipeline scheduling, memory planning, or diagnostics.

### Phase 1: Compiler and runtime foundation

**Duration:** Weeks 5 through 10

**Deliverables:**

- repository and CI skeleton.
- pinned toolchain and developer container.
- CobraProgram, CobraEffect, CobraPlacement, and CobraRuntime dialect skeletons.
- TableGen operation definitions and verifiers.
- `cobra-opt` and parser-printer round trips.
- native runtime library with task, event, device, stream, and allocation abstractions.
- Python native extension with one capture entry point.
- benchmark harness and machine metadata collector.
- artifact and cache format drafts.
- initial security threat model.

**TDD target:**

- every operation has verifier tests.
- every native runtime primitive has unit tests.
- parser and artifact readers have fuzz targets.
- CI can execute a trivial captured function through reference and Cobra paths.

**Exit criteria:**

- a pure two-node DAG can be captured, serialized, loaded, scheduled, and explained.
- debug and release builds pass sanitizers applicable to the current code.
- release-like wheels install in a clean container.

### Phase 2: Python capture, guards, effects, and graph breaks

**Duration:** Weeks 11 through 16

**Deliverables:**

- callable decorator and capture context.
- proxy values for supported tensor and dataframe boundaries.
- input guards for type, dtype, shape, stride, device, and selected constants.
- graph breaks with stable reason identifiers.
- conservative effect and alias analysis.
- exception and fallback semantics.
- source maps from Python locations to Cobra IR.
- `cobra explain` with capture and graph-break reports.
- shadow execution mode.

**Supported capture surface at this phase:**

- function calls.
- local control-flow boundaries represented conservatively.
- PyTorch tensor operations captured through an adapter.
- selected pandas, cuDF, NumPy, and PyArrow boundaries.
- pure Python orchestration around captured native calls.
- explicit opaque regions for unsupported code.

**Exit criteria:**

- 25 curated programs match eager execution.
- generated guards correctly trigger recompile or fallback.
- unsupported mutation and I/O graph-break safely.
- shadow mode can detect an intentionally injected wrong-code fault.

### Phase 3: Single-GPU optimizer and scheduler

**Duration:** Weeks 17 through 24

**Deliverables:**

- dependency DAG construction.
- conservative auto-parallel region discovery.
- CUDA stream and event scheduler.
- memory residency tracking.
- transfer elimination and DLPack or Arrow handoff paths.
- PyTorch backend integration.
- cuDF execution adapter.
- CUDA Graph region capture.
- first cost model.
- local compilation and plan cache.
- end-to-end profiling trace.

**Target demonstrations:**

1. Independent models overlap safely on one GPU when resources permit.
2. A dataframe remains on GPU through tensor conversion and inference where supported.
3. A repeated launch-heavy region uses CUDA Graph replay.
4. Cobra rejects an unprofitable plan and uses the reference path.

**Exit criteria:**

- v0.1 correctness and benchmark gates in Section 24 pass.
- no known silent wrong-code.
- diagnostics explain the selected execution plan.

### Milestone: v0.1 developer preview

**Expected range:** End of month 5 through month 6

The purpose of v0.1 is to prove the architecture and economic mechanism on a tightly controlled stack. It is not a claim of general Python compatibility.

### Phase 4: Coverage, native regions, and product hardening

**Duration:** Months 7 through 9

**Deliverables:**

- broader dynamic-shape guards.
- better effect and alias summaries.
- expanded PyTorch and dataframe operation coverage.
- typed scalar and simple NumPy region lowering to LLVM.
- more generated Triton kernels where a vendor or framework backend is inadequate.
- improved memory planner.
- compile-time budget management.
- reproducible AOT artifact prototype.
- remote-cache protocol draft.
- structured telemetry with opt-in default.
- partner workload ingestion kit.

**Exit criteria:**

- at least two design partners can run shadow mode on real workloads.
- the fallback boundary is stable and observable.
- native CPU regions outperform CPython enough to justify continued investment.

### Phase 5: Multi-GPU, experimental training, and beta qualification

**Duration:** Months 10 through 12

**Deliverables:**

- same-node multi-GPU placement.
- peer-to-peer transfer planning where supported.
- NCCL collective representation and ordering.
- independent-branch multi-GPU execution.
- experimental forward and backward capture.
- gradient and optimizer-state semantic tests.
- expanded CUDA architecture matrix.
- 72-hour stress qualification.
- partner canary controls and rollback.
- beta documentation and migration policy.

**Exit criteria:**

- beta gates in Section 24 pass.
- at least three external workloads provide profiler and cost evidence.
- unsupported training features fail safely or fall back.

### Milestone: Beta

**Expected range:** Month 11 through month 12

Beta means the product is suitable for controlled non-critical production trials with explicit support boundaries. It does not mean complete Python, pandas, NumPy, or PyTorch compatibility.

### Phase 6: Stable APIs, AOT, production hardening, and v1

**Duration:** Months 13 through 18, with up to month 21 reserved for qualification findings

**Deliverables:**

- stable Python API.
- stable C plugin ABI.
- versioned AOT artifact format.
- qualified single-node multi-GPU runtime.
- native CPU region backend.
- qualified Triton backend and selected CUDA Tile path.
- signed artifact workflow.
- production resource controls.
- independent security review.
- complete support and compatibility policy.
- LTS and patch process.
- enterprise deployment and air-gap procedures.
- public benchmark methodology and results.

**Exit criteria:**

- v1 gates in Section 24 pass without exceptions hidden in release notes.
- all known release-critical correctness defects are resolved or the affected feature is disabled by default.
- partner canaries demonstrate rollback and operational safety.

### Milestone: v1.0

**Expected range:** Month 18 through month 21

v1 is a stable production foundation for the declared support matrix. Multi-node distributed execution, complete training coverage, and full Python compatibility remain post-v1 programs unless validated earlier without compromising the core release.

---

## 24. Formal release gates

### 24.1 Severity definitions

| Severity | Definition | Release effect |
|---|---|---|
| Sev 1 | Silent wrong-code, data corruption, remote code execution, artifact trust bypass, or unrecoverable cross-tenant exposure. | Blocks every release. Affected optimization is disabled immediately. |
| Sev 2 | Crash, deadlock, leak, incorrect exception behavior, or severe resource exhaustion on a supported configuration. | Blocks the milestone unless the feature is removed from support and disabled by default. |
| Sev 3 | Diagnosable fallback, unsupported operation, non-critical performance regression, or usability defect. | May ship only within published budgets and with clear diagnostics. |
| Sev 4 | Documentation, cosmetic, or low-impact tooling issue. | Tracked, but does not normally block. |

### 24.2 v0.1 developer preview scope

#### Supported platform

- Linux x86_64 only.
- one fully qualified CPython minor version.
- one fully qualified PyTorch minor version.
- one fully qualified CUDA Toolkit line and documented driver floor.
- one primary NVIDIA GPU architecture for performance qualification.
- smoke correctness on at least one additional NVIDIA architecture where hardware is available.
- single process and single GPU.
- inference and batch-oriented workloads.

Exact versions are frozen at release-branch creation.

#### Required capabilities

- `@cobra.compile` and capture context.
- conservative graph breaks and eager fallback.
- guards for tensor type, dtype, shape, stride, and device.
- PyTorch graph handoff to an existing production-quality backend.
- selected pandas or cuDF relational operations.
- selected NumPy and PyArrow interchange paths.
- DLPack or Arrow-based low-copy boundaries where semantically valid.
- dependency graph and effect-aware parallel discovery.
- one-GPU CUDA stream scheduling.
- CUDA event synchronization.
- CUDA Graph capture for eligible repeated regions.
- local plan cache.
- `cobra explain`, `cobra doctor`, and `cobra benchmark`.
- shadow mode.
- feature flags for every optimizer family.

#### Explicitly out of scope

- general Python compilation.
- arbitrary classes and reflection.
- multi-GPU.
- distributed execution.
- production training support.
- stable artifact compatibility.
- stable plugin ABI.
- guaranteed acceleration for every workload.

#### v0.1 correctness gates

- zero known Sev 1 and Sev 2 correctness defects in enabled features.
- 50 curated end-to-end and integration programs.
- at least 25,000 generated property and differential cases across qualification runs.
- at least 10 million cumulative fuzz executions across artifact, IR, guard, and scheduler targets, with no unresolved reproducible crash.
- exact or operation-specific numerical agreement with reference execution.
- all enabled MLIR passes have positive and legality-negative tests.
- AddressSanitizer and UndefinedBehaviorSanitizer clean.
- ThreadSanitizer clean for supported CPU concurrency paths.
- CUDA Compute Sanitizer clean for release-critical generated kernels and scheduler tests.
- 24-hour repeated compile and execute soak.
- no monotonic host or device memory leak.
- steady-state memory growth no greater than 1 percent over the final 80 percent of the soak, after accounting for bounded caches.
- at least 100,000 successful repeated pipeline executions without divergence, deadlock, or resource exhaustion.

#### v0.1 performance gates

On the frozen benchmark host and v0.1-supported end-to-end suite:

- at least 1.25x geometric-mean warm speedup over B0.
- at least three pipelines show at least 1.10x speedup over B1 with a bootstrap 95 percent confidence interval excluding 1.00x.
- no pipeline that Cobra labels profitable is more than 5 percent slower than B1 outside the calibrated noise interval. The cost model must fall back otherwise.
- at least two pipelines reduce total host-to-device plus device-to-host bytes by 30 percent or more.
- at least two pipelines demonstrate measurable branch or transfer overlap and at least 10 percent lower critical-path latency attributable to that overlap.
- fallback-only execution adds no more than 5 percent warm overhead at p50 relative to B0 for representative unsupported programs.
- cache-hit artifact loading and guard setup are included in reported warm latency.
- compilation break-even is reported for every workload and is no greater than 100 executions for at least half of the intended repeated server workloads.

These are release gates, not universal performance promises. Every unsupported or regressed case remains visible in the report.

#### v0.1 product gates

- clean install from a wheel on the reference environment.
- actionable diagnostics for every graph break in the qualification corpus.
- one command produces a complete benchmark report.
- one command disables Cobra and returns to normal application behavior.
- documentation contains installation, first pipeline, explain, benchmark, fallback, and troubleshooting guides.
- benchmark raw data and reproduction scripts are published.
- license, notices, SBOM, and security policy are present.

### 24.3 Beta scope

#### Supported platform

- Linux x86_64.
- two current CPython minor versions plus one explicitly selected enterprise baseline when feasible.
- at least two supported PyTorch minor lines or one line plus a documented rapid qualification process.
- Ampere, Hopper, and Blackwell class NVIDIA systems represented in correctness testing.
- single GPU and same-node multi-GPU.
- inference production trials.
- experimental training, opt-in only.

#### Required capabilities

Everything in v0.1, plus:

- broader dynamic-shape and stride guards.
- native typed scalar and simple NumPy CPU regions.
- broader dataframe operation coverage.
- multi-GPU independent-branch scheduling.
- selected NCCL collectives represented in the plan.
- peer-to-peer transfer awareness.
- experimental forward and backward support.
- AOT artifact preview.
- remote-cache protocol preview.
- design-partner shadow and canary modes.
- profiler export suitable for Nsight Systems.

#### Beta correctness gates

- zero known Sev 1 defects.
- zero known Sev 2 defects in default-enabled capabilities.
- 200 curated programs.
- at least 250,000 generated property and differential cases.
- at least 100 million cumulative fuzz executions with no unresolved release-critical crash.
- complete sanitizer matrix for release-critical components.
- 72-hour single-GPU soak and 48-hour multi-GPU soak.
- no monotonic memory, stream, event, file-descriptor, or cache leak.
- multi-GPU failure injection validates cancellation and cleanup.
- gradient and optimizer differential tests pass for every training feature labeled supported.
- 30 days of shadow or canary operation across at least three external design-partner workloads, with no unresolved Sev 1 divergence.

#### Beta performance gates

- at least 1.40x geometric-mean speedup over B0 on the supported Cobra pipeline suite.
- at least 1.15x geometric-mean speedup over B1 on the subset with a genuine cross-library optimization opportunity.
- at least 70 percent of supported benchmark workloads run within 15 percent of B2 or outperform it.
- at least three real partner workloads reduce GPU-seconds or end-to-end compute cost by 15 percent or more without application-level semantic rewrites.
- fallback-only p50 overhead no greater than 3 percent.
- no default-enabled critical workload has an unexplained p99 regression greater than 5 percent against B1.
- multi-GPU scheduling shows positive scaling on at least two representative independent-branch workloads after communication cost.

#### Beta product and operational gates

- documented rollback and feature-disable procedure.
- semantically versioned beta Python API.
- artifact format carries compatibility metadata and fails closed.
- optional telemetry meets the privacy contract.
- partner issue triage and support process exists.
- upgrade and downgrade tests pass across consecutive beta releases.
- public limitations and unsupported features are complete enough to prevent false expectations.

### 24.4 v1.0 scope

#### Supported platform

- Linux x86_64.
- at least two current CPython minor versions and one documented enterprise baseline when operationally justified.
- declared PyTorch, pandas, NumPy, PyArrow, RAPIDS, CUDA, and driver matrix.
- at least three NVIDIA architecture generations in the qualification lab.
- single GPU and same-node multi-GPU.
- stable inference and batch pipelines.
- only the training capabilities that independently satisfy v1 gates.

#### Required capabilities

- stable public Python API.
- stable versioned C plugin ABI.
- versioned AOT artifact.
- JIT and AOT parity for supported regions.
- native CPU lowering for declared typed regions.
- qualified Triton backend.
- qualified selected CUDA Tile backend or an explicit decision to defer it based on evidence.
- effect-aware single-node multi-GPU scheduling.
- stable local cache and production remote-cache protocol.
- deterministic mode.
- shadow and canary deployment controls.
- signed artifact policy.
- complete diagnostics and profiler export.
- documented LTS and patch policy.

#### v1 correctness and reliability gates

- zero known Sev 1 and Sev 2 defects in supported default capabilities.
- 500 curated programs.
- at least 1 million generated property and differential cases.
- at least 500 million cumulative fuzz executions over the release cycle with no unresolved release-critical crash.
- seven-day continuous mixed-workload soak on the primary reference system.
- 72-hour same-node multi-GPU stress test.
- no monotonic resource leak.
- clean release sanitizer qualification.
- independent security assessment covering artifact loading, caches, native extensions, and compiler worker isolation.
- signed, provenance-attested artifacts with SBOM.
- 30-day partner canary on the final candidate with no Sev 1 wrong-code and no unresolved default-path Sev 2 issue.
- disaster recovery, cache corruption, driver error, OOM, and cancellation drills pass.

#### v1 performance and economic gates

- at least 1.50x geometric-mean speedup over B0 across the supported end-to-end suite.
- at least 1.20x geometric-mean speedup over B1 across the cross-library optimization subset.
- at least five representative external or production-grade workloads reduce GPU-seconds or total compute cost by 20 percent or more.
- at least 80 percent of supported benchmark workloads are within 15 percent of B2 or better.
- fallback-only p50 overhead no greater than 2 percent.
- no default-enabled release-critical workload has an unexplained p99 regression greater than 5 percent against its strongest automatic baseline.
- cache-hit execution and artifact loading meet documented service startup budgets.
- compilation break-even and expected cost savings are exposed through `cobra explain` or `cobra benchmark`.

#### v1 product and governance gates

- API reference and architecture documentation complete.
- compatibility and deprecation policies active.
- contributor governance operating publicly.
- security response process tested.
- license and generated-output policy reviewed by counsel.
- third-party redistribution manifest complete.
- enterprise and community feature boundary documented.
- at least one complete air-gapped installation procedure tested if offered commercially.

### 24.5 What v1 does not need to claim

v1 does not require:

- full Python language compatibility.
- all pandas or PyTorch operations.
- multi-node distributed training.
- every accelerator vendor.
- replacement of cuBLAS, cuDNN, TensorRT, or other optimized vendor libraries.
- speedup on workloads too small to amortize compilation and scheduling.

A narrow, truthful, highly reliable v1 is more valuable than a broad compiler that silently changes behavior.

---

## 25. Team and operating model

### 25.1 Minimum credible team

A credible path to the stated scope requires approximately 8 to 10 full-time engineers, plus product and executive ownership.

| Role | Initial count | Primary ownership |
|---|---:|---|
| Chief architect or technical founder | 1 | Technical thesis, architecture, scope, external technical relationships, final design arbitration. |
| Compiler and MLIR engineers | 2 | Dialects, analyses, passes, lowering, diagnostics, artifact model. |
| GPU compiler and performance engineers | 2 | Triton, CUDA Tile experiments, CUDA Graphs, profiling, kernel and library dispatch. |
| Python and framework integration engineers | 2 | Capture, guards, PyTorch, pandas, cuDF, NumPy, PyArrow, packaging. |
| Runtime and distributed systems engineer | 1 | Scheduler, memory planner, CUDA resources, multi-GPU, NCCL, cancellation. |
| Benchmark and reliability engineer | 1 | Harness, controlled lab, statistical analysis, fuzzing, soak, release qualification. |
| Developer experience, release, and security engineer | 1 | CLI, docs, wheels, CI, provenance, SBOM, vulnerability process. |

Some roles can initially be combined by unusually broad engineers, but benchmark and correctness ownership must remain independent enough to challenge optimizer claims.

### 25.2 Team topology

Use three tightly connected areas:

```text
Frontend and adapters
        |
Compiler and planner
        |
Runtime and backends
```

A fourth horizontal function owns:

```text
Correctness, benchmarks, release qualification, and security
```

No backend team should be able to approve its own performance claim without benchmark-owner review.

### 25.3 Decision process

Major decisions use short RFCs and architecture decision records.

RFC required for:

- new dialect or public IR concept.
- semantic behavior change.
- public API.
- new backend.
- new dependency with binary or licensing implications.
- artifact compatibility change.
- telemetry change.
- optimizer enabled by default.

The chief architect resolves deadlocks, but dissent and benchmark evidence remain recorded.

### 25.4 Engineering cadence

Recommended cadence:

- daily automated correctness status.
- twice-weekly optimizer and profiler review.
- weekly benchmark trend review.
- biweekly design review.
- monthly milestone gate with explicit continue, narrow, or stop decisions.
- quarterly external advisory review during beta and later.

### 25.5 Hardware lab

At minimum, maintain:

- one primary controlled development and benchmark GPU host.
- one additional architecture for compatibility.
- access to a current high-end architecture before beta.
- a same-node multi-GPU system before beta.
- isolated storage for benchmark datasets.
- monitoring for clock, thermal, power, and driver state.

Cloud GPUs can supplement the lab, but stable release benchmarks need reserved or dedicated hosts with known variance.

---

## 26. Licensing, governance, and commercial model

### 26.1 Recommended open-source license

Use:

```text
Apache License 2.0 WITH LLVM Exceptions
SPDX: Apache-2.0 WITH LLVM-exception
```

Apply it to:

- compiler core.
- runtime core.
- MLIR dialects and passes.
- Python SDK.
- CLI.
- reference adapters.
- benchmark harness.
- documentation and examples, unless a documentation-specific license is intentionally selected.

### 26.2 Why this is the most enterprise-attractive choice

Apache 2.0 is widely accepted by enterprise legal and procurement teams because it provides:

- permissive commercial use.
- modification and redistribution rights.
- explicit patent grants from contributors.
- patent-termination protection.
- notice requirements that are operationally manageable.
- no reciprocal source-disclosure obligation.

The LLVM exception is particularly suitable for compiler infrastructure. It reduces friction around linking and combined works in scenarios common to compiler and runtime ecosystems. It also aligns Cobra with the license model of LLVM and MLIR, which will be a foundational dependency.

The project must separately state:

> Cobra imposes no Cobra project license on user source code or compiler-generated output. Rights in user inputs and outputs remain with the applicable rightsholders, except that Cobra runtime components physically included in an artifact retain their own license and notice obligations.

This statement should appear in the FAQ and artifact documentation. It is not a substitute for legal review of linked third-party components.

### 26.3 Why not the common alternatives

| License | Reason not recommended for the core |
|---|---|
| MIT | Very permissive, but lacks Apache 2.0's explicit patent grant and termination framework, which matters for compiler and accelerator IP. |
| BSD-2-Clause or BSD-3-Clause | Enterprise-friendly, but similarly weaker on explicit patent terms. |
| GPL or LGPL | Creates adoption and linking questions for proprietary AI applications and generated deployment artifacts. |
| AGPL | Strong procurement resistance for infrastructure embedded in services and cloud products. |
| SSPL | Not generally recognized as open source and creates material cloud-service restrictions. |
| BSL | Delayed-open model can deter ecosystem contributors and strategic platform adoption. |
| Custom source-available license | Legal review friction, ecosystem distrust, and weak package-distribution compatibility. |

### 26.4 Contributor policy

Start with:

- Developer Certificate of Origin 1.1.
- per-commit sign-off.
- contributor-retained copyright.
- public contribution guidelines.
- no broad copyright-assignment CLA.

A DCO is lighter and more community-friendly than a CLA. A CLA should be introduced only if a clearly justified business model requires relicensing or patent terms not covered by Apache 2.0. Introducing a CLA later is difficult, so this decision must be revisited before accepting large external contributions if dual licensing is seriously contemplated.

### 26.5 Trademark

The software license does not grant rights to the Cobra name or logo beyond nominative use. Publish a simple trademark policy allowing:

- factual compatibility statements.
- community groups and integrations with clear non-endorsement wording.
- forks under a distinct product name.

Before public launch, perform professional trademark clearance in relevant software and cloud-service classes.

### 26.6 Open-core commercial boundary

Keep performance-critical local technology open. Enterprises will hesitate to adopt an optimizer if essential correctness or speed is held behind a proprietary wall.

Recommended proprietary products and services:

- fleet-wide compilation and artifact cache.
- fleet autotuning and hardware-specific plan distribution.
- policy and governance control plane.
- signed enterprise artifact registry.
- organization-wide performance analytics.
- audit retention and compliance exports.
- workload admission and quota policies.
- air-gapped enterprise distribution.
- certified compatibility images.
- long-term support releases.
- premium support and performance engineering.
- private adapters for enterprise systems.

Recommended open components:

- local compiler and runtime.
- local cache.
- core optimizers.
- CUDA backend essentials.
- standard PyTorch, pandas, cuDF, NumPy, and Arrow adapters.
- benchmark harness.
- file artifact inspection.
- correctness and fallback machinery.

The commercial product should sell fleet leverage, operational trust, governance, and support, not an artificially crippled compiler.

### 26.7 Dependency and redistribution policy

Maintain a machine-readable third-party inventory containing:

```text
name
version
source URL
license
linkage type
modified or unmodified
redistributed or external
notice requirement
patent or trademark notes
```

Special care is required for CUDA Toolkit components. Cobra should prefer detecting system-installed CUDA libraries and linking according to documented NVIDIA terms. Redistribution of any NVIDIA binary must be individually validated against the applicable license and redistribution list.

### 26.8 Governance after beta

Create a Technical Steering Committee with:

- public meeting notes.
- an RFC process.
- maintainer nomination criteria.
- conflict-of-interest disclosure.
- release authority rules.
- security embargo rules.

Avoid governance that makes Cobra appear to be an abandoned corporate code dump or a one-customer fork.

### 26.9 Patent posture

Recommended posture:

- rely on Apache 2.0 contributor patent grants.
- document patents known to be intentionally practiced by the project after legal review.
- consider a defensive patent pledge for Cobra-specific patents.
- avoid patent aggression against good-faith users and contributors.
- conduct freedom-to-operate review before commercial v1 in areas such as automatic placement, graph compilation, and heterogeneous scheduling.

This plan is a product recommendation, not legal advice. Final license and patent language requires qualified counsel.

---

## 27. NVIDIA alignment and engagement plan

### 27.1 Why Cobra can matter to NVIDIA

Cobra can create value for NVIDIA when it:

- increases useful work per GPU.
- makes CUDA-X libraries reachable from ordinary Python pipelines.
- reduces CPU dispatch and transfer bottlenecks that leave GPUs idle.
- makes CUDA Graphs, NCCL, Triton, and CUDA Tile easier to consume.
- converts heterogeneous AI applications into larger, more optimizable GPU regions.
- provides evidence that new GPU generations improve complete application economics, not only kernel microbenchmarks.

This alignment does not imply NVIDIA endorsement. Interest must be earned with data.

### 27.2 NVIDIA-first, architecture-portable strategy

Adopt:

```text
CUDA first
architecture portable
```

The compiler IR should not encode CUDA assumptions into general semantic layers. The first optimized backend should nevertheless exploit NVIDIA deeply rather than target a weak common denominator.

### 27.3 Integration sequence

1. PyTorch and existing NVIDIA-accelerated framework backends.
2. cuDF and Arrow or DLPack interchange.
3. CUDA streams and events.
4. CUDA Graphs.
5. cuBLAS, cuDNN, CUTLASS, and other mature libraries through supported interfaces.
6. NCCL for same-node multi-GPU.
7. Triton for custom fused kernels.
8. CUDA Tile for selected kernels after its toolchain and performance behavior satisfy Cobra qualification.
9. Optional TensorRT or TensorRT-LLM adapters for deployment workloads where they are the strongest backend.

### 27.4 What to demonstrate before approaching NVIDIA

Prepare a reproducible technical package containing:

- three real cross-library workloads.
- B0, B1, B2, and B3 results.
- Nsight Systems traces before and after.
- transfer-byte reduction.
- kernel-launch reduction.
- overlap and GPU-idle reduction.
- GPU-seconds or cost improvement.
- proof that the application source remained substantially unchanged.
- a clear list of CUDA technologies Cobra causes developers to consume automatically.

A strong opening demo is:

```text
ordinary pandas plus PyTorch pipeline
  -> Cobra captures whole-program dependencies
  -> supported preprocessing remains on GPU
  -> independent models overlap
  -> repeated region uses CUDA Graphs
  -> same result, lower GPU-seconds
```

### 27.5 Reasonable early asks

After evidence exists, reasonable asks include:

- architecture and API feedback.
- access to current and upcoming GPU systems under appropriate terms.
- CUDA Tile and compiler engineering guidance.
- profiling and performance review.
- developer program or startup program support.
- joint validation on reference workloads.
- eventual ecosystem listing or technical content.

Do not begin with an acquisition, investment, or exclusive partnership pitch. Begin with a measurable technical contribution to CUDA adoption and GPU efficiency.

### 27.6 Strategic tension

A fully vendor-neutral scheduler can reduce hardware lock-in, which benefits users but may be less strategically compelling to a hardware vendor. Cobra should preserve portable IR while making the NVIDIA backend unquestionably excellent.

Do not grant backend exclusivity that prevents future customer-driven portability. Any strategic agreement should preserve:

- independent core governance.
- customer control of artifacts and data.
- the right to implement other backends.
- publication of general benchmark methodology.

---

## 28. Principal risks and mitigations

| Risk | Likelihood | Impact | Mitigation and gate |
|---|---|---|---|
| Scope expands into compiling all Python | High | Critical | Keep explicit non-goals, region capture, graph breaks, and milestone scope. Stop features that do not improve target pipelines. |
| Python mutation and effects create wrong-code | High | Critical | Conservative effect model, unknown means ordered, shadow mode, differential testing, zero-tolerance wrong-code policy. |
| Alias analysis misses shared storage | Medium to high | Critical | Allocation identity, framework view metadata, conservative runtime guards, serialize uncertain writes. |
| Exceptions change due to parallel execution | Medium | High | Define commit order, delay externally visible result commitment, cancel dependent work, test exception races. |
| Randomness becomes nondeterministic | High | High | Explicit RNG effects and token model, deterministic mode, independent streams only with declared semantics. |
| Upstream PyTorch, pandas, RAPIDS, or CUDA changes break adapters | High | High | Thin versioned adapters, compatibility lab, pinned releases, fast disable path, upstream contribution strategy. |
| Cobra only beats eager, not existing compilers | Medium | Critical | B1 is a mandatory baseline from Phase 0. Stop or narrow the project if cross-library value is not measurable. |
| Generated kernels underperform vendor libraries | High | Medium | Library-first dispatch, generated kernels only for gaps or fusion opportunities, benchmark each kernel family. |
| Dynamic shapes trigger recompilation storms | High | High | Symbolic dimensions, guard widening, compile budgets, generic fallback, recompile counters and limits. |
| Scheduler overhead exceeds saved time | Medium | High | Profitability gate, native low-overhead runtime, task coarsening, microbenchmarks, eager fallback. |
| GPU memory overlap causes OOM | High | High | Memory-aware scheduling, reservation model, retry with serialized plan, fail-safe cleanup. |
| Dataframe GPU execution changes semantics | Medium | Critical | Metadata-aware differential matrix, operation whitelist, fallback on unsupported semantics. |
| Zero-copy handoff has lifetime bugs | Medium | Critical | Explicit ownership tokens, deleter contracts, stream synchronization, sanitizer and failure tests. |
| Benchmark results are invalid due to asynchronous timing | Medium | Critical | Dual CUDA-event and wall timing, explicit synchronization, independent benchmark review, published raw traces. |
| Autotuning increases startup or production variance | Medium | Medium | Bounded budgets, offline mode, cache, conservative default, kill switch. |
| CUDA-first strategy creates unacceptable vendor dependency | Medium | Medium | Portable semantic IR, backend boundary, no CUDA concepts in frontend contracts, post-v1 backend plan. |
| CUDA redistribution violates license terms | Low to medium | High | Dependency manifest, system-library preference, counsel review, CI wheel inspection. |
| Remote cache becomes code-injection vector | Medium | Critical | Signed content-addressed artifacts, strict parsing, sandboxed compilation, trust policies. |
| Enterprise users fear source or data leakage | Medium | High | Telemetry off by default, no source upload, local compiler, artifact inspection, air-gap path. |
| Team lacks compiler depth | Medium | Critical | Hire senior MLIR and GPU compiler engineers early, use external reviewers, narrow scope until expertise exists. |
| Hardware access delays qualification | Medium | High | Reserve dedicated lab capacity before beta, maintain cloud alternatives, avoid promising unsupported architectures. |
| Training support consumes the roadmap | High | High | Keep training experimental through beta, promote features individually only after gradient and optimizer gates. |
| Project name conflicts | Medium | Medium | Trademark search, use `cobra-compiler` distribution, reserve names before announcement. |

### 28.1 Stop conditions

Leadership should pause or narrow Cobra when any of these persist after a milestone review:

- no repeatable improvement over B1 on representative workloads.
- cross-library optimization requires extensive user rewrites.
- correctness requires so much serialization that target speedups disappear.
- maintenance cost of upstream adapters exceeds delivery capacity.
- compile and scheduling overhead cannot be amortized in target deployments.
- prospective users value diagnostics but not execution optimization.

A narrowed product can still be valuable. Examples include a Python AI pipeline profiler, a GPU residency planner, or an automatic concurrency runtime.

---

## 29. First 90 days execution plan

### Days 1 through 10: Foundation and benchmark truth

- appoint technical owners.
- create repository, license, DCO, contribution policy, and security contact.
- freeze three prototype workloads and all four baselines.
- provision the primary benchmark host.
- implement machine metadata collection.
- capture Nsight Systems traces of B0 and B1.
- write ADRs for scope, semantics, MLIR, runtime, and licensing.
- define the first correctness oracle for each workload.

**Output:** A baseline report with no Cobra claims.

### Days 11 through 20: Disposable whole-program tracer

- trace Python call boundaries.
- identify tensor, dataframe, and opaque Python regions.
- record data dependencies and observable effects manually or conservatively.
- record device, dtype, shape, stride, and allocation identity.
- render a program DAG.
- calculate approximate critical path and available parallelism.

**Output:** `cobra trace` prototype and visual DAG.

### Days 21 through 30: Three high-risk experiments

#### Experiment A: Parallel branch scheduler

Run two independent model branches using separate CUDA streams. Validate outputs, exception behavior, resource limits, and actual overlap.

#### Experiment B: Dataframe-to-tensor residency

Exercise pandas or cuDF preprocessing followed by a tensor model. Measure copies and evaluate Arrow or DLPack handoff.

#### Experiment C: Repeated-region launch optimization

Capture an eligible sequence with CUDA Graphs and measure warm replay economics.

**Go or narrow review at day 30:**

At least one experiment must show a statistically valid 15 percent improvement over B1 and a clear whole-program mechanism. Otherwise narrow the thesis before building compiler infrastructure.

### Days 31 through 45: Real compiler skeleton

- pin LLVM and MLIR.
- implement CobraProgram and CobraEffect operations.
- add verifiers and parser-printer tests.
- create Python native extension.
- lower the disposable trace into Cobra IR.
- implement source locations and explain output.
- add artifact-parser fuzzing.

**Output:** Captured prototype workload visible in `cobra-opt`.

### Days 46 through 60: Guards, graph breaks, and reference execution

- implement type, dtype, shape, stride, and device guards.
- define cache keys.
- implement opaque regions and graph breaks.
- implement shadow mode.
- build the first differential corpus.
- establish wrong-code incident workflow.

**Output:** 15 curated programs execute through capture, fallback, and shadow comparison.

### Days 61 through 75: Scheduler and CUDA runtime

- implement native DAG scheduler.
- add CUDA streams and events.
- model memory reservations.
- implement deterministic simulation tests.
- support cancellation and kernel failure propagation.
- measure scheduler overhead.

**Output:** Safe one-GPU parallel fan-out and fan-in through the actual runtime.

### Days 76 through 90: Integrated evidence package

- connect PyTorch backend.
- connect selected cuDF path.
- implement low-copy boundary prototype.
- add CUDA Graph plan nodes.
- build cost-model version zero.
- implement `cobra explain` summary.
- run B0 through B3 on all three prototypes.
- publish internal raw results, limitations, and failures.

**Day 90 decision criteria:**

- no semantic divergence in the qualification corpus.
- at least 70 percent of target operations or runtime weight captured in one representative pipeline.
- at least one cross-library pipeline exceeds B1 by 15 percent.
- at least one pipeline eliminates a measurable transfer or materialization boundary.
- scheduler overhead is small enough to preserve the measured gain.
- a credible route exists to v0.1 gates within the following 12 to 16 weeks.

If these criteria fail, the team must explicitly choose to stop, narrow, or redefine the target market.

---

## 30. Definition of Done

### 30.1 Definition of Done for a compiler optimization

An optimization is done when:

- semantic contract is documented.
- legality conditions are implemented and tested.
- positive and negative IR tests pass.
- eager differential tests pass.
- property and edge-case tests pass.
- diagnostics identify when it applies and why it does not.
- feature flag and rollback path exist.
- benchmark demonstrates the intended mechanism.
- no material regression appears in the broader suite.
- sanitizer and fuzz coverage is updated where applicable.
- documentation and release note are complete.

### 30.2 Definition of Done for a framework adapter

An adapter is done when:

- supported version matrix is explicit.
- operation coverage is machine-readable.
- unsupported behavior falls back safely.
- values and metadata match the reference.
- alias and lifetime rules are documented.
- conversion-copy behavior is measured.
- upstream error behavior is preserved or clearly wrapped.
- adapter can be disabled independently.
- clean-install package tests pass.

### 30.3 Definition of Done for a backend

A backend is done when:

- capability discovery is reliable.
- generated or selected code is correctness-qualified.
- resource cleanup works under failure.
- artifact compatibility is validated.
- profiler symbols and source maps exist.
- performance is compared to the strongest relevant backend.
- unsupported hardware fails clearly.
- license and redistribution review is complete.

### 30.4 Definition of Done for a release

A release is done only when:

- its formal gate in Section 24 passes.
- candidate binaries are the exact binaries qualified.
- benchmark and correctness reports are archived.
- known issues are public and specific.
- support matrix is published.
- SBOM, checksums, signatures, notices, and provenance are present.
- rollback path is tested.
- security contact and patch branch are ready.
- installation and tutorial have been tested by someone outside the core implementation team.

---

## 31. Recommended final product thesis

Cobra should not be presented as a universal replacement for CPython, pandas, PyTorch, CUDA, or expert kernel engineering.

Its precise thesis is:

> **Cobra is an AI-native whole-program optimizer and heterogeneous runtime that captures ordinary Python AI pipelines, proves safe dependencies, and automatically chooses parallel execution, data placement, memory movement, graph capture, vendor libraries, and generated kernels across CPU and NVIDIA GPUs.**

The engineering promise is:

```text
same declared program semantics
less orchestration overhead
fewer unnecessary data movements
more useful concurrency
better GPU-seconds per unit of work
clear fallback when optimization is unsafe or unprofitable
```

The strategic differentiator is not a faster individual tensor operation. It is optimization across the boundaries where Python, dataframes, tensors, models, devices, and multiple independent branches meet.

The first proof must be economic and reproducible:

> **Cobra must deliver more useful AI work from the GPUs a customer already owns, without requiring the customer to rewrite the application as a distributed CUDA program.**

---

## 32. Primary technical references

The following primary sources should be pinned in the architecture reading list. Version-specific behavior must always be revalidated against the versions in Cobra's support matrix.

1. LLVM Project licensing, Apache License 2.0 with LLVM Exceptions: https://llvm.org/LICENSE.txt
2. SPDX identifier for the LLVM exception: https://spdx.org/licenses/LLVM-exception.html
3. MLIR dialect documentation: https://mlir.llvm.org/docs/Dialects/
4. MLIR Operation Definition Specification and TableGen: https://mlir.llvm.org/docs/DefiningDialects/Operations/
5. MLIR GPU dialect: https://mlir.llvm.org/docs/Dialects/GPU/
6. MLIR NVGPU dialect: https://mlir.llvm.org/docs/Dialects/NVGPU/
7. MLIR Async dialect: https://mlir.llvm.org/docs/Dialects/AsyncDialect/
8. MLIR Linalg dialect: https://mlir.llvm.org/docs/Dialects/Linalg/
9. PyTorch `torch.compile`: https://docs.pytorch.org/docs/stable/generated/torch.compile.html
10. PyTorch custom backends: https://docs.pytorch.org/docs/stable/torch.compiler_custom_backends.html
11. PyTorch graph breaks: https://docs.pytorch.org/docs/stable/compile/programming_model.common_graph_breaks.html
12. PyTorch AOTInductor: https://docs.pytorch.org/docs/stable/torch.compiler_aot_inductor.html
13. TorchBench: https://github.com/pytorch/benchmark
14. Triton language and compiler: https://triton-lang.org/
15. RAPIDS cuDF pandas accelerator mode: https://docs.rapids.ai/api/cudf/stable/cudf_pandas/
16. Apache Arrow C Data Interface: https://arrow.apache.org/docs/format/CDataInterface.html
17. Apache Arrow C Device Data Interface: https://arrow.apache.org/docs/format/CDeviceDataInterface.html
18. DLPack: https://dmlc.github.io/dlpack/latest/
19. Substrait specification: https://substrait.io/
20. NVIDIA CUDA Graphs: https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#cuda-graphs
21. NVIDIA NCCL: https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/
22. NVIDIA cuTile Python and CUDA Tile model: https://docs.nvidia.com/cuda/cutile-python/index.html
23. NVIDIA Nsight Systems: https://docs.nvidia.com/nsight-systems/
24. NVIDIA Nsight Compute: https://docs.nvidia.com/nsight-compute/
25. NVIDIA CUDA Compute Sanitizer: https://docs.nvidia.com/compute-sanitizer/
26. LLVM testing guide: https://llvm.org/docs/TestingGuide.html
27. LLVM FileCheck: https://llvm.org/docs/CommandGuide/FileCheck.html
28. Google Benchmark: https://github.com/google/benchmark
29. Python `pyperf`: https://pyperf.readthedocs.io/
30. Apache License 2.0: https://www.apache.org/licenses/LICENSE-2.0
31. Developer Certificate of Origin 1.1: https://developercertificate.org/
32. NVIDIA CUDA Toolkit end-user license agreement: https://docs.nvidia.com/cuda/eula/
33. Codon, useful prior art for native Python compilation: https://github.com/exaloop/codon
34. Bend and HVM, useful prior art for implicit parallelism: https://github.com/HigherOrderCO/Bend

---

## 33. Benchmark execution runbook

This runbook is the required operational procedure for any performance result used in a pull request, milestone review, public claim, or partner report.

### 33.1 Benchmark manifest

Every benchmark run begins with a versioned manifest:

```yaml
run_id: cobra-2026-08-10-primary-host
suite: pipelines-v0.1
commit: <cobra-git-sha>
workload_commit: <benchmark-git-sha>
container_digest: <oci-digest>

host:
  hostname_alias: primary-bench-01
  os: ubuntu
  kernel: <captured-value>
  cpu: <captured-value>
  numa_nodes: <captured-value>
  memory_gb: <captured-value>

cuda:
  driver: <captured-value>
  toolkit: <captured-value>
  gpu_name: <captured-value>
  gpu_uuid_hash: <captured-value>
  compute_capability: <captured-value>
  clocks_policy: locked-or-default
  power_limit_watts: <captured-value>
  persistence_mode: true
  mig: disabled

software:
  python: <captured-value>
  pytorch: <captured-value>
  triton: <captured-value>
  pandas: <captured-value>
  cudf: <captured-value>
  numpy: <captured-value>
  pyarrow: <captured-value>

protocol:
  warmup_policy: stability
  minimum_samples: 30
  configuration_order: randomized
  correctness_required: true
  confidence_interval: bootstrap-95
```

The harness captures values directly where possible. Hand-entered metadata is rejected for release evidence unless marked and justified.

### 33.2 Host preparation

Before a controlled benchmark:

1. Reserve the host exclusively.
2. Record current driver, firmware, kernel, CPU governor, GPU clocks, power, thermal, and MIG state.
3. Stop unrelated scheduled jobs and monitoring agents known to create material load.
4. Confirm available disk space and local dataset placement.
5. Clear only the caches explicitly covered by the test protocol. Do not clear operating-system caches for a warm-production benchmark unless the production scenario does so.
6. Run a noise calibration benchmark.
7. Reject the host when variance or throttling exceeds the suite threshold.

Proposed command:

```bash
cobra-bench doctor --strict --output artifacts/environment.json
```

### 33.3 Build and artifact preparation

```bash
git checkout <qualified-commit>

cmake --preset benchmark
cmake --build --preset benchmark --target cobra-all

uv sync --frozen --extra benchmark

cobra-bench prepare \
  --suite benchmarks/suites/pipelines-v0.1.yaml \
  --output artifacts/prepared
```

The benchmark build must retain enough symbols for profiling while preserving release-equivalent optimization flags.

### 33.4 Correctness qualification before timing

Run the workload once under each configuration and compare outputs:

```bash
cobra-bench verify \
  --suite benchmarks/suites/pipelines-v0.1.yaml \
  --variants b0,b1,b2,b3 \
  --output artifacts/correctness
```

A failed or skipped correctness oracle invalidates performance results for that workload.

For floating-point workloads, the suite manifest records the exact comparator:

```yaml
correctness:
  comparator: tensor
  rtol_by_dtype:
    float16: <approved-value>
    bfloat16: <approved-value>
    float32: <approved-value>
  atol_by_dtype:
    float16: <approved-value>
    bfloat16: <approved-value>
    float32: <approved-value>
  equal_nan: true
```

Tolerance values are established per operation family and framework behavior. They are never loosened merely to pass Cobra output.

### 33.5 Cold-path measurement

Cold measurements use fresh process state and a controlled cache state.

```bash
cobra-bench run \
  --suite benchmarks/suites/pipelines-v0.1.yaml \
  --variants b0,b1,b2,b3 \
  --phase cold \
  --process-per-sample \
  --randomize-order \
  --output artifacts/raw/cold
```

Record separately:

- Python process startup.
- framework import.
- Cobra capture.
- compilation.
- autotuning.
- artifact serialization.
- first execution.

Do not merge these into one opaque number when evaluating compile amortization.

### 33.6 Warm-path measurement

```bash
cobra-bench run \
  --suite benchmarks/suites/pipelines-v0.1.yaml \
  --variants b0,b1,b2,b3 \
  --phase warm \
  --warmup stability \
  --min-samples 30 \
  --randomize-order \
  --validate-every-sample \
  --output artifacts/raw/warm
```

The stability warm-up policy should stop only when:

- a minimum warm-up count is met.
- recent median values remain within a configured band.
- no thermal throttling is detected.
- GPU memory and compilation state have stabilized.

A maximum warm-up count prevents infinite warm-up loops and is reported as a failure when reached.

### 33.7 Profiler evidence

For every headline speedup, collect a profiler trace:

```bash
cobra-bench profile \
  --suite benchmarks/suites/pipelines-v0.1.yaml \
  --workload multimodal_fanout \
  --variants b1,b3 \
  --tool nsight-systems \
  --output artifacts/profiles
```

Use Nsight Compute selectively for kernel-level questions:

```bash
cobra-bench profile \
  --suite benchmarks/suites/pipelines-v0.1.yaml \
  --workload <name> \
  --variant b3 \
  --tool nsight-compute \
  --kernel-filter <pattern> \
  --output artifacts/profiles
```

The reviewer must be able to connect the result to at least one measured mechanism:

- removed transfer.
- reduced synchronization.
- reduced launch count.
- increased overlap.
- improved kernel.
- avoided materialization.
- improved placement.

### 33.8 Statistical analysis

```bash
cobra-bench analyze \
  --input artifacts/raw \
  --confidence bootstrap-95 \
  --primary-metric latency_ms \
  --geomean-group end_to_end \
  --output artifacts/analysis
```

The analysis output contains:

```text
summary.md
summary.json
samples.parquet
confidence_intervals.csv
regressions.json
break_even.json
plots/
```

No plot may hide absolute timing, sample count, confidence interval, unsupported workloads, or correctness status.

### 33.9 Release comparison

```bash
cobra-bench compare \
  --candidate artifacts/analysis/summary.json \
  --baseline benchmark-history/v0.1-last-qualified.json \
  --policy benchmarks/policies/release-v0.1.yaml \
  --fail-on-regression
```

The comparison checks:

- suite geometric mean.
- critical-workload p50 and p99.
- compilation time.
- fallback overhead.
- transfer bytes.
- memory.
- unsupported coverage changes.
- correctness and crash status.

### 33.10 Result schema

Each sample should include fields similar to:

```json
{
  "run_id": "...",
  "workload": "multimodal_fanout",
  "variant": "b3",
  "phase": "warm",
  "sample": 17,
  "correct": true,
  "wall_time_ns": 123456789,
  "gpu_time_ns": 101000000,
  "cpu_time_ns": 32000000,
  "peak_host_bytes": 0,
  "peak_device_bytes": 0,
  "h2d_bytes": 0,
  "d2h_bytes": 0,
  "kernel_launches": 0,
  "graph_breaks": 0,
  "fallback_nodes": 0,
  "compile_time_ns": 0,
  "cache_hit": true,
  "guard_failures": 0,
  "gpu_temperature_c": 0,
  "throttled": false
}
```

Zero values in this example are placeholders. The harness must distinguish a real zero from an unavailable metric.

### 33.11 Benchmark anti-patterns

The following invalidate a performance claim:

- measuring asynchronous GPU work without correct synchronization.
- comparing a warm Cobra run to a cold baseline.
- excluding compilation while presenting one-shot latency.
- changing batch size, precision, model mode, data, or numerical flags between variants.
- allowing Cobra to omit work or materialize fewer outputs than the baseline.
- selecting only workloads Cobra wins.
- using a hand-tuned B2 implementation as though it were B1.
- reporting GPU utilization without latency, throughput, and profiler context.
- using shared cloud hardware for final release claims without variance controls.
- loosening correctness tolerances after seeing a mismatch.
- dropping outliers without a recorded machine-level reason.

### 33.12 Minimum public benchmark report

A public report must answer:

1. What exact source and environment were tested?
2. What did each baseline enable?
3. Which workloads were unsupported?
4. Were cold and warm paths separated?
5. How was correctness checked?
6. What were sample counts and confidence intervals?
7. What mechanism produced each major gain?
8. How much compilation was required?
9. When does the optimization break even?
10. How did memory and transfer behavior change?
11. Which workloads regressed?
12. Can an external engineer reproduce the result?

---

## 34. Test and CI command matrix

The commands below are proposed repository contracts. Exact target names may evolve before v0.1, but each test category and cadence is mandatory.

### 34.1 Local pre-commit sequence

```bash
uv run ruff check python test benchmarks
uv run ruff format --check python test benchmarks
uv run mypy python/cobra_compiler

cmake --preset dev
cmake --build --preset dev --target cobra-all

cmake --build --preset dev --target check-cobra-unit
cmake --build --preset dev --target check-cobra-lit
uv run pytest -q test/python
```

A repository helper should provide:

```bash
./scripts/test-changed.sh
```

It maps changed files to the minimum safe test set while CI remains authoritative.

### 34.2 Complete CPU correctness lane

```bash
cmake --preset asan-ubsan
cmake --build --preset asan-ubsan --target cobra-all
ctest --preset asan-ubsan --output-on-failure

cmake --build --preset asan-ubsan --target check-cobra-lit
uv run pytest test/python test/integration/cpu -n auto
uv run pytest test/property --hypothesis-profile=ci
```

### 34.3 Thread-safety lane

```bash
cmake --preset tsan
cmake --build --preset tsan --target cobra-runtime-tests
ctest --preset tsan --output-on-failure
```

CUDA code is excluded from incompatible sanitizer processes and tested in its dedicated lanes.

### 34.4 GPU correctness lane

```bash
cobra doctor --strict

uv run pytest test/integration/cuda -m "gpu and not long"
uv run pytest test/differential -m "gpu and release_critical"

compute-sanitizer --tool memcheck \
  ./build/debug/bin/cobra-cuda-tests --gtest_filter='ReleaseCritical*'

compute-sanitizer --tool racecheck \
  ./build/debug/bin/cobra-cuda-tests --gtest_filter='Scheduler*'

compute-sanitizer --tool synccheck \
  ./build/debug/bin/cobra-cuda-tests --gtest_filter='GeneratedKernel*'

compute-sanitizer --tool initcheck \
  ./build/debug/bin/cobra-cuda-tests --gtest_filter='GeneratedKernel*'
```

### 34.5 IR and pass lane

```bash
./build/dev/bin/llvm-lit -sv test/Dialect
./build/dev/bin/llvm-lit -sv test/Analysis
./build/dev/bin/llvm-lit -sv test/Optimizer
./build/dev/bin/llvm-lit -sv test/Conversion
```

Every optimizer test file should make legality visible:

```text
RUN: cobra-opt %s --cobra-parallelize | FileCheck %s
RUN: cobra-opt %s --cobra-parallelize --verify-each | FileCheck %s --check-prefix=SAFE
```

### 34.6 Differential and shadow lane

```bash
uv run pytest test/differential \
  --cobra-reference=eager \
  --cobra-mode=shadow \
  --maxfail=1
```

Nightly runs expand seeds and shape ranges:

```bash
uv run pytest test/differential test/property \
  --hypothesis-profile=nightly \
  --cobra-random-seeds=1000
```

### 34.7 Fuzz lane

```bash
./build/fuzz/bin/cobra_artifact_fuzzer \
  -max_total_time=3600 corpus/artifact

./build/fuzz/bin/cobra_guard_fuzzer \
  -max_total_time=3600 corpus/guards

./build/fuzz/bin/cobra_scheduler_fuzzer \
  -max_total_time=3600 corpus/scheduler

./build/fuzz/bin/cobra_ir_bytecode_fuzzer \
  -max_total_time=3600 corpus/ir
```

Longer continuous fuzzing runs in dedicated infrastructure and periodically merges minimized corpus entries into the repository.

### 34.8 Packaging lane

```bash
python -m build
python -m twine check dist/*

python -m venv /tmp/cobra-clean
/tmp/cobra-clean/bin/pip install dist/cobra_compiler-*.whl
/tmp/cobra-clean/bin/cobra doctor
/tmp/cobra-clean/bin/cobra run examples/smoke.py

./scripts/audit-wheel.sh dist/*.whl
./scripts/check-third-party-notices.sh dist/*.whl
./scripts/generate-and-verify-sbom.sh dist/*.whl
```

### 34.9 Benchmark lane

```bash
cobra-bench verify --suite benchmarks/suites/pr.yaml --variants b0,b1,b3
cobra-bench run --suite benchmarks/suites/pr.yaml --phase warm
cobra-bench compare --candidate artifacts/analysis/summary.json \
  --baseline benchmark-history/main.json \
  --policy benchmarks/policies/pr.yaml
```

Release lanes replace `pr.yaml` with the full frozen suite and include B2.

### 34.10 Cadence matrix

| Test group | Local | Pull request | Nightly | Weekly hardware matrix | Release candidate |
|---|---:|---:|---:|---:|---:|
| Formatting and static analysis | Yes | Yes | Yes | Yes | Yes |
| C++ and Python unit tests | Selected | Full | Full | Full | Full |
| MLIR pass tests | Selected | Full | Full | Full | Full |
| CPU sanitizer tests | Optional | Selected | Full | Full | Full |
| GPU differential tests | Smoke | Selected | Full | Full matrix | Full matrix |
| CUDA Compute Sanitizer | Targeted | Selected | Full critical set | Full | Full |
| Property tests | Small | Medium | Large | Large | Maximum qualified profile |
| Fuzz tests | Reproducer | Short | Hours | Extended | Cumulative gate plus targeted rerun |
| Packaging | Smoke | Full primary wheel | Full matrix | Full matrix | Full release matrix |
| Microbenchmarks | Changed areas | Fast set | Full | Full | Full |
| End-to-end benchmarks | Optional | Smoke | Full primary host | Full hardware set | Frozen qualification suite |
| Soak tests | No | No | Short | 24 hours as scheduled | Milestone duration |
| Security scans and SBOM | Optional | Yes | Yes | Yes | Yes plus manual review |
| Documentation examples | Selected | Full | Full | Full | Full |

### 34.11 Required test ownership

Each test suite has a named owner and backup. Flaky tests are defects and must be quarantined only with:

- an issue.
- an owner.
- an expiration date.
- a preserved signal or replacement gate.

A test may not be silently retried until green. Retries are recorded and count toward flakiness metrics.

---

## 35. v0.1 issue-ready epic backlog

### Epic 0: Project foundation and governance

**Deliverables:**

- license, DCO, contribution guide, governance draft, security policy.
- repository, build presets, CI, code ownership.
- pinned toolchain and support manifest.
- ADR template and first architecture records.

**Acceptance criteria:**

- clean clone builds in the documented container.
- CPU smoke tests run in CI.
- GPU runner validates a trivial CUDA call.
- release artifact can be signed in a dry run.

### Epic 1: Cobra MLIR substrate

**Deliverables:**

- CobraProgram, CobraEffect, CobraTensor, CobraDataFrame, CobraPlacement, and CobraRuntime dialect minimums.
- operation definitions, verifiers, parser-printer, bytecode tests.
- `cobra-opt` and `cobra-translate`.

**Acceptance criteria:**

- representative v0.1 program round-trips text and bytecode.
- malformed operations fail with source-located diagnostics.
- all operation families have positive and negative tests.

### Epic 2: Python capture frontend

**Deliverables:**

- decorator and context API.
- input proxy system.
- callable and source fingerprinting.
- source mapping.
- graph-break infrastructure.

**Acceptance criteria:**

- supported calls emit graph nodes.
- unsupported calls materialize only required dependencies.
- graph breaks include stable reason identifiers and source locations.
- reference execution remains available at all times.

### Epic 3: Guards and specialization cache

**Deliverables:**

- guards for type, dtype, shape, stride, device, selected constants, model identity, and framework version.
- guard widening policy.
- content-addressed local cache.
- integrity validation.

**Acceptance criteria:**

- matching calls hit cache.
- mismatching calls recompile or fall back according to budget.
- cache corruption fails closed.
- recompilation storm test respects configured limits.

### Epic 4: Effects, aliases, and semantic barriers

**Deliverables:**

- effect taxonomy.
- alias-set representation.
- conservative summaries for supported adapters.
- ordered I/O and mutation barriers.
- exception commit model.
- RNG policy.

**Acceptance criteria:**

- independent reads are parallel candidates.
- conflicting writes serialize.
- views alias base storage.
- unknown effects serialize in safe mode.
- exception, mutation, and random differential tests pass.

### Epic 5: PyTorch adapter

**Deliverables:**

- tensor metadata capture.
- supported graph handoff.
- custom backend bridge.
- graph-break translation.
- output and alias reconstruction.

**Acceptance criteria:**

- selected v0.1 tensor regions compile through the chosen PyTorch backend.
- dynamic-guard failure is safe.
- non-contiguous, empty, and alias cases in the supported matrix match eager.
- backend can be disabled independently.

### Epic 6: Dataframe and Arrow adapter

**Deliverables:**

- selected dataframe relational nodes.
- pandas and cuDF dispatch.
- schema and index metadata.
- Arrow interchange.
- explicit fallback boundaries.

**Acceptance criteria:**

- filter, projection, selected groupby, selected join, and dataframe-to-tensor paths pass the declared semantic matrix.
- null, index, ordering, and categorical metadata are validated.
- unsupported operations return to pandas without corrupting the graph.

### Epic 7: DLPack and memory ownership

**Deliverables:**

- tensor handoff contracts.
- allocation identity.
- lifetime tokens and deleters.
- stream-correct synchronization.
- copy accounting.

**Acceptance criteria:**

- eligible transfers are low-copy or zero-copy according to the interface contract.
- producer lifetime outlives all consumers.
- cross-stream tests pass.
- double-free, use-after-free, and early-release fault tests pass.

### Epic 8: Single-GPU runtime and scheduler

**Deliverables:**

- DAG executor.
- CUDA stream pool.
- event management.
- cancellation.
- memory reservations.
- virtual-clock scheduler test harness.

**Acceptance criteria:**

- fan-out and fan-in execute correctly.
- independent branches overlap on qualifying hardware.
- OOM retries with a safer serialized plan when configured.
- failure and cancellation release resources.
- scheduler overhead meets the v0.1 microbenchmark budget.

### Epic 9: Global optimizer and cost model

**Deliverables:**

- dependency construction.
- transfer elimination.
- placement version zero.
- task coarsening.
- profitability gate.
- CUDA Graph candidate detection.

**Acceptance criteria:**

- optimizer never parallelizes known conflicts.
- unprofitable plans are rejected.
- explain output shows estimated and observed costs.
- target benchmark mechanisms are visible in transformed IR.

### Epic 10: CUDA Graph and generated-kernel path

**Deliverables:**

- CUDA Graph capture and replay node.
- selected Triton template path.
- kernel cache.
- source maps and profiler labels.

**Acceptance criteria:**

- eligible stable regions replay correctly.
- guard changes invalidate incompatible captures.
- generated kernels pass full dtype and shape tests.
- vendor-library dispatch remains preferred when stronger.

### Epic 11: Developer experience

**Deliverables:**

- `cobra run`.
- `cobra explain`.
- `cobra benchmark`.
- `cobra doctor`.
- trace export.
- installation and troubleshooting docs.

**Acceptance criteria:**

- a new engineer can install and run the tutorial from a clean environment.
- every qualification graph break has a useful message.
- explain report includes captures, effects, aliases, placement, transfers, parallel regions, guards, and fallback.

### Epic 12: Qualification and v0.1 release

**Deliverables:**

- 50-program correctness corpus.
- property and fuzz qualification.
- sanitizer qualification.
- controlled benchmark report.
- 24-hour soak.
- signed wheel, source archive, notices, SBOM, provenance.

**Acceptance criteria:**

- every v0.1 gate in Section 24.2 passes.
- release candidate is promoted without rebuilding.
- public limitations and benchmark raw data are available.
- rollback and feature-disable drills pass.

---

## 36. Approval record

Before implementation begins, the project sponsors should explicitly approve:

- the narrow v0.1 scope.
- the semantic charter.
- the B1 benchmark baseline.
- the Apache-2.0 WITH LLVM-exception recommendation, subject to counsel.
- the CUDA-first and architecture-portable strategy.
- the 8 to 10 engineer staffing assumption or a correspondingly reduced scope.
- the Phase 0 and day-90 stop conditions.
- the rule that no performance result overrides a correctness failure.

Suggested sign-off fields:

```text
Executive sponsor:
Chief architect:
Compiler lead:
GPU/runtime lead:
Correctness and benchmark owner:
Security owner:
Legal reviewer:
Date:
Approved scope revision:
```
