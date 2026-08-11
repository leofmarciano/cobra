# S27 — Packaging, wheels, SBOM

| Field | Value |
|---|---|
| Milestone | M4 — v0.1 hardening & release |
| Depends on | S26 (done) |
| Hardware | CPU-only (install tests also run on GPU host) |
| Estimated sessions | 2-3 |
| Plan sections | §16.2-16.4, §19.16, §34.8, §22.6, §26.7 |

## Objective

Turn the build into distributable, auditable artifacts: manylinux wheels
under the `cobra-compiler` name, clean-environment install tests,
SBOM + license machinery, and a reproducible release pipeline dry-run.
"Developer laptops must never be a release authority" (§16.4).

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §16.2 (build outputs), §16.3 (wheel
   strategy + CUDA bundling rules), §16.4 (reproducibility list),
   §19.16 (packaging test list), §34.8 (lane commands), §26.7
   (redistribution inventory)
3. Build system state (S06 presets, S09 extension build)

## Out of scope

- Actually publishing to PyPI (human decision at S29). Signed-artifact
  PKI beyond a dry-run key (v1 hardens). `.cobra` AOT artifact format
  (post-v0.1). Conda packages.

## Tasks

### T1 — Wheel build
- [ ] Do: scikit-build-core + cibuildwheel config for manylinux
  (documented glibc baseline per §16.3) targeting the pinned Python;
  native libs (`libcobra_runtime`, `libcobra_compiler`, `_native`)
  packaged with correct RPATHs; **no NVIDIA library bundled** — CUDA
  discovered at runtime from the system/torch installation, and a
  wheel-content scan enforces the §16.3 rule ("every bundled NVIDIA
  library must appear in a redistribution manifest" — v0.1 policy:
  bundle none).
- Accept: `python -m build` + cibuildwheel produce installable wheels;
  scan proves zero bundled CUDA/vendor binaries; `twine check` passes.

### T2 — Clean-install test battery (§19.16)
- [ ] Do: scripted: fresh venv → install wheel → `cobra doctor` →
  compile+run smoke pipeline → **GPU-absent fallback verified** (CPU
  machine: everything works eager, clear diagnostics, §19.16) →
  no undeclared host-library deps (`auditwheel`/ldd check) →
  uninstall cleanly. Run on: CPU-only container AND the GPU host.
- Accept: battery scripted + green on both environments; wired as the
  packaging CI lane (§34.8).

### T3 — SBOM, licenses, notices
- [ ] Do: generate SPDX + CycloneDX SBOMs for wheel + native deps;
  license scan (all deps vs Apache-2.0 compatibility); populate
  `THIRD_PARTY_NOTICES.md` from the §26.7 machine-readable inventory
  (`third-party.yaml`: name/version/source/license/linkage/modified/
  redistributed/notice); CI drift check (new dep without inventory
  entry = red).
- Accept: SBOMs validate; inventory covers every shipped component;
  drift check demonstrated on a branch.

### T4 — Reproducible release pipeline dry-run
- [ ] Do: release workflow building from a clean container (pinned
  digest): source archive + wheels + checksums + SBOM + provenance
  attestation stub + signed tag dry-run (local key); verify two
  consecutive clean builds produce identical wheels within documented
  tolerances (§16.4) — document any nondeterminism found + mitigation.
- Accept: `docs/process/release.md` documents the pipeline; dry-run
  artifacts + reproducibility report committed.

### T5 — Version/support policy files
- [ ] Do: finalize `support-matrix.yaml` for v0.1 (one CPython, one
  torch minor, one CUDA line, driver floor, GPU family tested — §24.2
  platform scope, values from the GPU host reality); version scheme
  doc (0.x rules per §21.3); `cobra doctor` validates the runtime env
  against this file (already stubbed in S26 — verify + tighten).
- Accept: doctor rejects an unsupported combo with a clear message
  (test with fake env); matrix matches what CI actually tests (audit).

## Validation

```bash
python -m build && python -m twine check dist/*
./scripts/install-test.sh dist/cobra_compiler-*.whl     # clean venv battery
./scripts/audit-wheel.sh dist/*.whl                     # no vendor binaries
./scripts/generate-and-verify-sbom.sh dist/*.whl
./scripts/check-third-party-notices.sh
./scripts/check.sh
```

## Definition of Done

- [ ] All tasks accepted; §19.16 checklist fully automated and green
- [ ] Release pipeline documented + dry-run evidence committed
- [ ] STATE.md + Session log updated; committed on sprint branch

## Handoff to next sprint

S28 uses these artifacts for qualification (the wheel under test = the
wheel that would ship, §21.5: "promotion changes metadata, not binary
content"). PyPI name reservation is a human task — flag it in STATE's
Human-input queue now.

## Session log (append-only)

<!-- [YYYY-MM-DD][session] done / next / surprises -->
