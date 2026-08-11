# Contributing to Cobra

Thank you for your interest in contributing to the Cobra project.

## Developer Certificate of Origin

This project uses the Developer Certificate of Origin (DCO) 1.1. By submitting
a contribution, you certify the following:

```text
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.


Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

## Sign-off requirement

Every commit in a contribution must include a `Signed-off-by:` line in the
commit message, for example:

```text
My excellent fix

Signed-off-by: Random J Developer <random@developer.example.org>
```

You can add this automatically with `git commit -s`.

## How to contribute

1. Open or comment on an issue to discuss the change.
2. Create a topic branch from `main`.
3. Make focused, well-tested changes.
4. Ensure `./scripts/check.sh` passes locally.
5. Push your branch and open a pull request.

## AI-executed sprint loop

Day-to-day development of Cobra is driven by an AI-executed sprint loop
documented in `orchestration/PROTOCOL.md` and `orchestration/STATE.md`. The
loop coordinates Executor, Validator, Gatekeeper, and Recovery sessions.
Human contributors are welcome to open issues and pull requests; large
architectural or scope decisions are normally routed through the RFC and
ADR process described in `GOVERNANCE.md`.

## Code of conduct

All contributors are expected to follow `CODE_OF_CONDUCT.md`.
