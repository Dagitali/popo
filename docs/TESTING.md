<!--
TESTING.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Test selection, dependency boundaries, and validation responsibilities.

Maintainer Notes
- Keep commands aligned with Make and test configuration.
- Link to tests/README.md for fixture design instead of duplicating it.
-->

# Testing Guide

Choose checks according to their dependencies and side effects. The [tests overview] owns the layer
map, discovery rules, and fixture conventions; the [contributing guide] owns setup and review.

- [Set Up Development](#set-up-development)
- [Test Layers](#test-layers)
- [Dependency Boundaries](#dependency-boundaries)
- [Run Checks](#run-checks)
- [Test Design](#test-design)
- [Installation Boundary](#installation-boundary)

## Set Up Development

Use a Python version permitted by `pyproject.toml`. From the checkout:

```console
make dev PY=python3.13
make check
```

Use `PY=python3.14` for the other supported interpreter. Setup may download packages; ordinary
checks do not install tools implicitly. See the [development setup] for environment overrides.

## Test Layers

| Need | Command | Boundary |
| --- | --- | --- |
| Isolated checkers and repository contracts | `make test-unit` | Credential-free |
| CLI dispatch and reporting | `make test-integration` | Credential-free |
| Both default layers | `make test` | No artifact build |
| Distribution contents and metadata | `make test-distribution` | Builds temporary artifacts |
| Installed CLI behavior | `make test-installation` | Clean virtual environments |
| All layers | `make test-full` | Includes network-dependent artifact work |

The meta and e2e layers are opt-in. Marker filters apply only to selected paths; see the [discovery
rules] before invoking pytest directly.

## Dependency Boundaries

The lowest configuration uses `requirements/lowest.txt`; the newest configuration resolves the
newest versions allowed by package metadata. Reproduce them in separate environments using the
[dependency-boundary instructions]. `make dependency-policy` checks file consistency, not installed
versions. Dependabot proposals still require metadata and minimum pins to agree before merging.

## Run Checks

`make check` combines Ruff lint and formatting checks, strict mypy, default tests, and repository
policy checks. Run focused tests while iterating, then the full gate. Use `make docs-markdown` for
Markdown changes and `make check-release` for the same built wheel and sdist across artifact tests.

Report coverage without reducing test scope or thresholds to conceal failures:

```console
python -m pytest --cov=popo --cov-branch --cov-report=term-missing
```

## Test Design

Follow the [suite design] for class-based tests, parameterized scenarios, narrow fixtures, precise
diagnostics, and subprocess isolation. Test generic checker behavior independently of Popo's own
dependency versions; the repository self-check validates this checkout's configuration.

## Installation Boundary

Artifact tests may access package indexes and exercise installations outside the source checkout.
They do not publish packages or deploy cloud resources. The manual [installation workflow] extends
this validation across supported platforms; it is not an AWS deployment test. Review the [release
policy] for publication safeguards.

[installation workflow]: ../.github/workflows/deployment-test.yml
[contributing guide]: ../CONTRIBUTING.md
[development setup]: ../CONTRIBUTING.md#development-setup
[dependency-boundary instructions]: ../CONTRIBUTING.md#github-automation
[release policy]: ../RELEASE-POLICY.md
[tests overview]: ../tests/README.md
[discovery rules]: ../tests/README.md#discovery-and-selection
[suite design]: ../tests/README.md#suite-design
