<!--
README.md
popo/examples/cdk

Copyright © 2026 Dagitali LLC. All rights reserved.

Runnable Python CDK consumer with one local and CI guardrail policy.

Maintainer Notes
- Keep the example independently usable after copying it to a repository root.
- Keep execution evidence separate from static wiring and hosted enforcement.
-->

# Python CDK Guardrail Example

This Python-based AWS CDK consumer uses one explicit profile in `popo.toml`. Make, an installed pre-commit
hook, and the complete [CI workflow] all delegate to `make guardrails`. Popo checks documentation,
required files, action pins, dependency declarations, Python policy, and the delegation contract.
Application dependencies and execution remain separate from guardrail installation.

- [Run Locally](#run-locally)
- [Application Tests and Synthesis](#application-tests-and-synthesis)
- [Detect Drift](#detect-drift)
- [Use in CI](#use-in-ci)

## Run Locally

Copy this directory, including hidden files, into a new disposable directory outside the Popo
checkout. Run the following commands from that copy with Python 3.13 or 3.14, Git, Make, and a
POSIX-compatible shell available. Application checks are optional and described separately below.

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

## Application Tests and Synthesis

This example uses Python CDK v2 with exact `aws-cdk-lib` and `constructs` pins in both
`pyproject.toml` and `requirements.txt`. Popo's exact dependency comparison detects drift between
those files. Python policy also checks the preferred interpreter, mypy/Ruff declarations and CI
Python versions. No CDK library, Node.js runtime or AWS credentials are needed for `make
guardrails`.

To run the application separately, use Node.js 22 or 24 (24 recommended for this pinned library) and
install application dependencies in the activated example environment:

```console
python -m pip install -r requirements.txt
make test
make synth
```

`make test` inspects an in-memory template with the CDK assertions library and writes temporary
assembly files outside the source tree. `make synth` executes `app.py` and writes `cdk.out/`
locally. It uses the Python CDK API directly, so these commands do not install or require the CDK
CLI. `cdk.json` also records the app command for consumer-owned CDK tooling.

The stack is environment-agnostic: it has no context lookups, assets, account or region discovery.
It describes one private S3 bucket with encryption, public-access blocking, TLS enforcement and
retention. Tests and synthesis do not provision it. No bootstrap, deployment or destruction commands
are included. Popo's guards do not assess infrastructure security or replace template assertions,
CDK-specific analysis, or separately authorized deployment review. See the [CDK bucket reference].

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
from the same requirements file used locally, then runs `make guardrails`. No application dependency
installation or cloud credentials are required for this guardrail job. Add application tests and
analysis separately.

Popo's installed-package tests copy this example into temporary Git repositories and exercise Make,
actual installed Git hooks, and the workflow step's command with both wheel and sdist installations.
Those tests substitute the artifact under test for the pinned Popo dependency; they do not establish
that installing the example's Git pin or hosted CI succeeded. Git metadata and tool caches may
change during those execution tests; consumer source files must not change. The same acceptance
tests run for Swift, Python and CDK consumers.

Static parity does not prove hook installation, absence of `SKIP`, trigger coverage, check-source
identity, tool-version equivalence, or hosted branch enforcement. Conditions and suppressed failures
also need review. Do not retire existing controls until actual local and hosted runs are verified.

[CI workflow]: .github/workflows/ci.yml
[CDK bucket reference]: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_s3/Bucket.html
