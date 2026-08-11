# ADR-0003: License — Apache-2.0 with LLVM Exceptions

## Status

Accepted

## Context

The project needs a license that is permissive, enterprise-friendly, and aligned
with the compiler infrastructure Cobra will build on. Alternatives include MIT,
BSD-2/3-Clause, GPL/LGPL, AGPL, SSPL, BSL, and a custom source-available license.

## Decision

Cobra is licensed under the Apache License, Version 2.0, with LLVM Exceptions.
The SPDX identifier is `Apache-2.0 WITH LLVM-exception`.

Rationale (technical plan §26.1–26.3):

- Apache 2.0 provides an explicit patent grant and termination framework, which
  matters for compiler and accelerator IP.
- It is widely accepted by enterprise legal and procurement teams.
- The LLVM exception reduces friction around linking and combined works common
  in compiler and runtime ecosystems and aligns Cobra with LLVM and MLIR.
- MIT and BSD variants are weaker on explicit patent terms.
- GPL, LGPL, AGPL, SSPL, and BSL create adoption or linking concerns for
  proprietary AI applications and generated deployment artifacts.
- A custom source-available license would create legal-review friction and weak
  package-distribution compatibility.

The project separately states:

> Cobra imposes no Cobra project license on user source code or
> compiler-generated output. Rights in user inputs and outputs remain with the
> applicable rightsholders, except that Cobra runtime components physically
> included in an artifact retain their own license and notice obligations.

## Consequences

- Downstream users can combine Cobra with proprietary code with clear patent
  and linking expectations.
- Bundled third-party components must still be tracked in
  `THIRD_PARTY_NOTICES.md`.
- Final license language remains subject to qualified legal review before a
  public v1 release.
