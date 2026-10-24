<!--
README.md
popo/examples/swift

Copyright © 2026 Dagitali LLC. All rights reserved.

Runnable Swift consumer with one local and CI guardrail policy.

Maintainer Notes
- Keep the example independently usable after copying it to a repository root.
- Keep execution evidence separate from static wiring and hosted enforcement.
-->

# Swift Guardrail Example

This small [Swift package] uses one explicit profile in `popo.toml`. Make, an installed pre-commit
hook, and the complete [CI workflow] all delegate to `make guardrails`. Popo checks documentation,
required files, action pins, and that delegation contract without requiring `pyproject.toml`.

- [Run Locally](#run-locally)
- [Detect Drift](#detect-drift)
- [Use in CI](#use-in-ci)

## Run Locally

Copy this directory, including hidden files, into a new disposable directory outside the Popo
checkout. Run the following commands from that copy with Python 3.13 or 3.14, Git, Make, and a
POSIX-compatible shell available. A Swift 5.9-or-newer toolchain is needed only for `make test`.

```console
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-guardrails.txt
git init
pre-commit install
git add --all
make guardrails
pre-commit run --all-files --verbose
```

The staging step supplies Git's tracked-file inventory for `pre-commit run --all-files`; it affects
only your disposable copy. The hook also runs on subsequent commits. Installation can access the
network; guardrail execution reads local inputs. Review the shared tool pins before adoption. The
example pins Popo to a full Git revision rather than a moving branch.

Successful execution returns zero and prints `PASS: all configured repository checks passed`.
Inspect the selection with `popo explain --profile guardrails`. The Make target always specifies
that profile; bare `popo check-all` retains Popo's legacy defaults and is not this example's
command. The hook uses `always_run: true` and `pass_filenames: false` to inspect the whole
repository.

Run `make test` separately to compile and test the Swift library. Popo neither compiles Swift nor
replaces SwiftLint, SwiftFormat, package tests, or their existing consumer-owned configuration.

## Detect Drift

In the disposable copy, change one input at a time, run `make guardrails`, then restore it:

| Change | Expected failure |
| --- | --- |
| Append a second recipe command to `guardrails` | Recipe must be exactly the profile invocation |
| Add `args: [unexpected]` to the hook | Hook must invoke the canonical Make target without arguments |
| Change the CI step to `run: make another-target` | Declared CI step must run `make guardrails` |
| Set workflow run defaults to another working directory | Invocation must use the repository root |
| Add a Markdown link to a nonexistent local file | Local target does not exist |

The profile includes `check-guardrail-parity`, so it inspects its own wiring without executing Make
again. Extra recipe commands fail inspection before Make can reach them. Hook and workflow changes
are inspected as data. A broken Markdown link demonstrates that the shared policy itself runs, not
merely that the entry points look alike. All three callers must preserve failures.

## Use in CI

When the example is copied to a repository root, `.github/workflows/ci.yml` is a complete GitHub
Actions workflow. Inside Popo's `examples/` directory it is an inert consumer example. It installs
from the same requirements file used locally, then runs `make guardrails`. No Swift compiler or
cloud credentials are required for this guardrail job. Add Swift build/test jobs separately.

Popo's installed-package tests copy this example into temporary Git repositories and exercise Make,
actual installed Git hooks, and the workflow step's command with both wheel and sdist installations.
Those tests substitute the artifact under test for the pinned Popo dependency; they do not establish
that installing the example's Git pin or hosted CI succeeded. Git metadata and tool caches may
change during those execution tests; consumer source files must not change.

Static parity does not prove hook installation, absence of `SKIP`, trigger coverage, check-source
identity, tool-version equivalence, or hosted branch enforcement. Conditions and suppressed failures
also need review. Do not retire existing controls until actual local and hosted runs are verified.

[CI workflow]: .github/workflows/ci.yml
[Swift package]: Package.swift
