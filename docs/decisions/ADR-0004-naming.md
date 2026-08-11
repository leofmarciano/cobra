# ADR-0004: Package, import, and CLI names

## Status

Accepted

## Context

The public project name is "Cobra", but the plain `cobra` package name on PyPI is
already associated with an established Python project. We need stable names for
the distribution, the Python import namespace, and the command-line tool.

## Decision

- Distribution name on PyPI: `cobra-compiler`.
- Python import namespace: `cobra_compiler`.
- Command-line entry point: `cobra`.

Rationale (technical plan §16.3):

- `cobra-compiler` avoids a collision with the existing `cobra` package while
  keeping the project name discoverable.
- `cobra_compiler` is an explicit, unambiguous import namespace.
- `cobra` as a CLI remains short and user-facing, e.g. `cobra run app.py`.

A final trademark and package-name search is required before public release.
Until then, all naming is considered provisional and will be revisited at the
first gate.

## Consequences

- Users write `import cobra_compiler as cobra`.
- The package build is configured with a `cobra` console script.
- Release artifacts must reserve and validate the chosen distribution name.
