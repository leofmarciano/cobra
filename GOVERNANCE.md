# Cobra Governance (Draft)

This document describes how the Cobra project is governed during its initial
phase. It is a draft and will be reviewed at the first milestone gate.

## Roles

* **Project Owner**: Holds final decision authority, defines scope, approves
  major dependencies, and acts as security and conduct escalation contact.
* **AI Executors**: Autonomous agents that execute sprint tasks under the
  active sprint file, follow `orchestration/PROTOCOL.md`, and commit work.
* **Validators**: Independent sessions that verify and close sprints.
* **Contributors**: Human or automated participants submitting changes through
  the issue and pull request process.

## Decision process

Major decisions require a short RFC and an Architecture Decision Record (ADR).
RFCs are required for:

* new dialect or public IR concept,
* semantic behavior change,
* public API,
* new backend,
* new dependency with binary or licensing implications,
* artifact compatibility change,
* telemetry change,
* optimizer enabled by default.

The project owner resolves deadlocks. Dissent and benchmark evidence are
recorded in the ADR and the decision ledger.

## AI-executed sprint loop

The project is built by an autonomous loop defined in
`orchestration/PROTOCOL.md`. The active sprint is recorded in
`orchestration/STATE.md`. Each sprint runs on its own branch
(`sprint/S<NN>-<slug>`) and is merged into `main` only after validation.

## Contribution path

See `CONTRIBUTING.md` for the DCO, sign-off, and pull request process.

## Conduct and security

* Code of conduct: `CODE_OF_CONDUCT.md`
* Security policy: `SECURITY.md`
