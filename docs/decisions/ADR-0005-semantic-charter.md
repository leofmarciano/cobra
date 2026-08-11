# ADR-0005: Semantic charter (DRAFT)

## Status

Draft — frozen at the S05 gate review.

## Context

Cobra accelerates CPython-hosted programs by capturing, optimizing, and
scheduling whole-program execution across heterogeneous hardware. Any such
system must have a clear, testable contract with the user about when it is
allowed to transform a program and what guarantees remain intact. This charter
collects those guarantees in one place so that future sprints can write tests
against them.

## Charter

### 1. Effect rules and the conservative default

Every captured operation has an effect class. Parallelism and reordering are
allowed only when all of the following hold:

- data dependencies are satisfied,
- effect sets do not conflict,
- alias analysis proves no conflicting mutation,
- exception behavior can be preserved,
- estimated benefit exceeds scheduling and transfer overhead, and
- resource and memory budgets permit concurrency.

An operation whose effects are **unknown** is treated as a full barrier. It may
not be reordered past, fused through, or parallelized with any other effectful
operation unless a later analysis proves it safe. The default is safety; precision
is introduced only with tests and differential evidence.

### 2. Fallback contract

When Cobra cannot compile or safely optimize a region, it must fall back to
ordinary CPython execution. The fallback path must preserve observable Python
behavior. Cobra must **never silently**:

- skip an operation,
- reorder an unknown side effect,
- swallow or replace an exception,
- change a warning into silence,
- mutate an object differently, or
- use relaxed floating-point behavior in strict mode.

Fallback overhead budgets: v0.1 median no more than 5% for a fully unsupported
function after warm-up; beta no more than 3%; v1 no more than 2%.

### 3. Exception commit order

Parallel execution may cause multiple tasks to fail concurrently. Cobra must
preserve a deterministic approximation of Python source-order behavior:

1. Every scheduled task receives a source-order index.
2. If several pure parallel tasks fail, Cobra reports the exception from the
   earliest source-order task.
3. Later task failures are attached as suppressed diagnostics in debug mode.
4. Effectful operations are not reordered across potentially throwing operations
   unless safety is proven.
5. Cancellation is best effort and must not hide a previously selected exception.
6. Resource failures such as device OOM are reported with the selected schedule
   and fallback attempts.

### 4. Randomness and determinism modes

Stateful random number generation is an effect. Cobra exposes three modes:

- `--determinism=strict`: preserve RNG state order; do not parallelize
  operations sharing a stateful generator; capture and restore framework RNG
  states during shadow comparisons.
- `--determinism=reproducible`: allow parallel RNG only when the API is stateless
  or key-based, independent generators are explicit, and a reproducible
  partitioning policy is configured.
- `--determinism=off`: minimize constraints on RNG ordering; the user accepts
  non-determinism for performance.

### 5. Mutation and alias conservatism

Cobra needs library-specific alias models. Until a model is proven, the default
is conservative:

- For tensors: identify storage identity; distinguish views from copies; track
  strides, offsets, and version counters; treat in-place operations as writes
  to the storage alias set.
- For dataframes: distinguish logical plans from materialized mutable objects;
  model `inplace=True` and view-like behavior conservatively; treat unknown
  extension arrays as potential aliases; preserve pandas index and nullable
  semantics.
- For ordinary Python objects: default to unknown aliasing; improve precision
  only through immutable built-in types, dataclasses, frozen objects, and
  adapter metadata.

### 6. Guard philosophy

Compiled artifacts are valid only while their assumptions hold. Guards are
ordered from cheapest to most expensive and checked before dispatch. The policy
is:

1. Fast guards execute before dispatch.
2. A failed guard attempts a compatible cached specialization.
3. If none exists, Cobra recompiles within a configured budget.
4. Repeated specialization churn triggers eager fallback and a diagnostic.
5. The default maximum recompilations per region is configurable and must be
   conservative.

Guard classes include: Python function and code object identity; model object
identity and parameter version; tensor dtype, rank, shape, stride, layout, and
device; dataframe schema, dtypes, nullable behavior, and index assumptions;
library and ABI versions; CUDA driver, runtime, architecture, and backend
versions; effect annotation version; environment flags affecting semantics; and
math/determinism mode.

## Consequences

- Every optimization and scheduling pass must be able to cite the charter clause
  it relies on and the test that guards against violating it.
- Differential tests must exercise fallback, exceptions, RNG state, mutation,
  aliasing, and guard failure.
- This charter is frozen at the S05 gate; changes after that point require an
  RFC and an updated ADR.
