# ADR-0001: Scope and explicit non-goals through v1

## Status

Accepted

## Context

Cobra is an AI-native whole-program Python compiler and heterogeneous parallel
runtime. Defining what is deliberately out of scope is as important as defining
the scope, because the project operates with a small team and must reach
statistically valid benchmark evidence before expanding.

## Decision

Through v1, Cobra focuses on:

- Capturing whole-program Python execution across tensor, dataframe, and
  ordinary Python regions.
- Lowering captured programs into a Cobra program graph and MLIR-based IR.
- Scheduling independent work across CPU, CUDA streams, and eventually multiple
  GPUs while preserving observable Python behavior.
- Providing a safe fallback path to ordinary CPython execution when compilation
  or optimization is not possible.

Cobra explicitly does **not** target the following before v1 (see technical plan
§2.5):

- Full semantic replacement of CPython.
- Automatic compilation of every package on PyPI.
- Automatic partitioning of an arbitrary single model across a cluster.
- A new tensor framework replacing PyTorch, JAX, or TensorFlow.
- A new dataframe implementation replacing pandas or cuDF.
- Automatically outperforming cuBLAS, cuDNN, or every specialized kernel.
- Multi-node fault-tolerant cluster scheduling in the core v1 release.
- Perfect static proof of purity for arbitrary dynamic Python.
- Transparent acceleration of code that performs frequent unknown mutation or
  external I/O.
- Windows and macOS production support before the Linux implementation is
  mature.

## Consequences

- The team can concentrate on cross-library scheduling and safe fallback.
- Users should expect selective acceleration of well-behaved Python programs,
  not a universal drop-in replacement.
- Each non-goal can be revisited only after the current target market shows a
  statistically valid improvement.
