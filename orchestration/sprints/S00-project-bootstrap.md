# S00 — Project bootstrap & governance

| Field | Value |
|---|---|
| GitHub issue | #1 |
| Milestone | M0 — Thesis validation |
| Depends on | — |
| Hardware | CPU-only |
| Estimated sessions | 1-2 |
| Plan sections | §16.1, §16.3, §26.1, §26.4, §29 (Days 1-10), §35 Epic 0 |

## Objective

Turn the empty repo into a governed, linted, CI-checked project skeleton
matching the plan's repository layout — with governance docs, Python
packaging under the `cobra-compiler` name, ADR infrastructure, and a
drafted semantic charter. No compiler code.

## Context budget (read ONLY these)

1. `orchestration/STATE.md`, this file
2. `COBRA_TECHNICAL_PLAN.md` §16.1 (repo layout), §16.3 (packaging names),
   §26.1/§26.4 (license, DCO), §29 Days 1-10, §35 Epic 0
3. For T5 only: §6.5 (fallback contract), §8.1/§8.3/§8.4 (effects,
   exceptions, RNG) — the charter distills these.

## Out of scope

- CMake/C++/LLVM anything (S06). CI beyond lint+pytest (later sprints).
- Publishing to PyPI, pushing to GitHub, trademark search (human tasks).

## Tasks

### T1 — Governance documents
- [x] Do: Add `LICENSE` (Apache-2.0 text + LLVM Exceptions addendum —
  fetch canonical text from llvm.org/LICENSE.txt), `NOTICE`,
  `CONTRIBUTING.md` (DCO 1.1 quoted in full + sign-off requirement +
  pointer to orchestration loop), `CODE_OF_CONDUCT.md` (Contributor
  Covenant 2.1), `GOVERNANCE.md` (draft: solo owner + AI executors, RFC
  list from §25.3), `SECURITY.md` (private reporting; email comes from
  STATE.md Human-input queue — if unanswered, use a placeholder and flag
  it), `THIRD_PARTY_NOTICES.md` (empty table w/ §26.7 schema).
- Accept: files exist, license text is verbatim-canonical, DCO text is
  verbatim, no placeholder remains except a flagged security email.

### T2 — Repository skeleton (§16.1)
- [ ] Do: Create the §16.1 directory tree (`cmake/ docs/ include/cobra/
  lib/ python/cobra_compiler/ runtime/ tools/ test/ benchmarks/ examples/
  docker/ scripts/ .github/workflows/` with the listed subdirectories),
  each holding a one-paragraph `README.md` stating its purpose per the
  plan. Add `.gitignore` (Python, C++, CMake, `build/`, `third_party/`,
  `.cobra/cache/`, `artifacts/raw/` — but keep `artifacts/environment/`
  and `artifacts/analysis/` trackable), `.editorconfig`.
- Accept: tree matches §16.1 (git needs the READMEs to track dirs);
  `.gitignore` keeps `uv.lock` tracked.

### T3 — Python packaging
- [ ] Do: `pyproject.toml` — distribution `cobra-compiler`, import package
  `python/cobra_compiler/` (src layout via tool config), Python pinned to
  one minor version (choose current stable, record it in
  `support-matrix.yaml` v0 per §15.2 example), dev deps: `ruff`, `mypy`,
  `pytest`. Generate `uv.lock`. Add `python/cobra_compiler/__init__.py`
  with `__version__ = "0.0.1.dev0"` and a trivial
  `test/python/test_import.py`.
- Accept: `uv sync && uv run pytest test/python` green;
  `import cobra_compiler as cobra` works.

### T4 — ADR infrastructure + founding ADRs
- [ ] Do: `docs/decisions/TEMPLATE.md` (context/decision/status/
  consequences), then: ADR-0001 scope & non-goals (distill §2.5),
  ADR-0002 architecture: CPython-hosted capture + MLIR, not a fork
  (distill §4.2/§4.3 matrix), ADR-0003 license choice (§26.1-26.3),
  ADR-0004 naming: dist `cobra-compiler`, import `cobra_compiler`, CLI
  `cobra` (§16.3).
- Accept: each ADR ≤1 page, status `accepted`, cites its plan sections.

### T5 — Semantic charter DRAFT (ADR-0005)
- [ ] Do: `docs/decisions/ADR-0005-semantic-charter.md`, status `draft`
  (frozen at S05 gate). Must state, in normative language: effect rules
  (unknown = full barrier), fallback contract (the five "never silently"
  items of §6.5), exception commit order (§8.3 policy 1-6), RNG modes
  (§8.4), mutation/alias conservatism (§8.2 defaults), guard philosophy
  (§6.4 policy). One page max — this is the contract every future sprint
  tests against.
- Accept: charter contains all six areas with testable statements.

### T6 — Lint CI + repo hygiene
- [ ] Do: `.github/workflows/lint.yml` — on PR/push: `uv sync`, `ruff
  check`, `ruff format --check`, `mypy python/cobra_compiler`, `pytest`.
  Add `scripts/check.sh` running the same locally (per §34.1 spirit).
- Accept: `./scripts/check.sh` passes locally; workflow YAML is valid
  (`uvx --from yamllint yamllint` or equivalent).

## Validation

```bash
uv sync
./scripts/check.sh                     # ruff + mypy + pytest
git ls-files | grep -c "README.md"     # skeleton dirs tracked
uv run python -c "import cobra_compiler as cobra; print(cobra.__version__)"
```

## Definition of Done

- [ ] All tasks accepted; validation passes from a clean checkout
- [ ] No TODO/placeholder except flagged Human-input items
- [ ] STATE.md + Session log updated; committed on `sprint/S00-project-bootstrap`

## Handoff to next sprint

S01 builds the benchmark harness inside `benchmarks/harness/` using the
packaging + lint infra from this sprint.

## Session log (append-only)

<!-- [2026-08-10][Devin] Out-of-scope (human request): added autonomous Orca
loop harness scripts/cobra_orca_loop.py, wrapper, precheck, and README docs. No
sprint tasks completed; S00 still not_started. Next: run P0 or enable the
automation to begin S00. -->
<!-- [2026-08-10][Devin] Human request: created 30 GitHub issues (#1-#30) for
S00-S29, added labels `sprint`/`milestone-M*`/`gate`, and linked them from every
sprint file and from the ROADMAP ledger. -->
