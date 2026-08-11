# ADR-0002: CPython-hosted capture plus MLIR, not a fork

## Status

Accepted

## Context

Several existing systems could serve as a starting point for Cobra: a hard fork
of Codon, an extension of TorchDynamo only, a runtime built on Bend/HVM, or a
fully custom compiler. The choice determines compatibility risk, release
coupling, and how much cross-library control Cobra retains.

## Decision

Cobra is an independent compiler and runtime built on MLIR, CPython
integration, and existing AI backends. It does **not** begin as a hard fork of
Codon, PyTorch, Bend, or HVM.

Rationale (technical plan §4.2):

- Cobra's primary semantic contract is compatibility with ordinary CPython-hosted
  applications, including graceful fallback.
- The differentiator is cross-library program capture and scheduling, not only
  scalar Python compilation.
- A hard fork would couple Cobra's release cycle to another compiler's language
  semantics and internal architecture.
- Existing systems can be integrated as backends or adapters without
  surrendering Cobra's global program graph.

The decision matrix in §4.3 evaluated five options. The recommended option,
"Custom CPython-hosted capture plus MLIR", was chosen because it offers the
highest CPython compatibility and cross-library control and a strong GPU path
through adapters, despite the largest initial engineering load.

Codon may be used later as a research reference or optional CPU scalar-region
backend. Bend and HVM may be explored only for pure recursive tasks if a
measured workload justifies the integration. They are not the core runtime for
tensor and dataframe operations.

## Consequences

- Cobra owns its own program graph, effect model, and scheduling semantics.
- Integration work with PyTorch, pandas/cuDF, and other libraries is explicit
  rather than inherited.
- The project accepts a larger initial implementation burden in exchange for
  long-term architectural independence.
