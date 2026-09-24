<!--
README.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Test layout, selection, and artifact-validation boundaries.

Maintainer Notes
- Keep test paths synchronized with pytest, Make, and hosted workflows.
- Keep default tests independent of package-index access and cloud credentials.
-->

# Tests Overview

Tests are organized by scope rather than by feature. The root `conftest.py` assigns the matching
pytest marker from each test module's top-level directory.

- [Current Layout](#current-layout)
- [Discovery and Selection](#discovery-and-selection)
- [Dependency Prerequisites](#dependency-prerequisites)
- [Shared Fixtures](#shared-fixtures)
- [Suite Design](#suite-design)
- [Common Commands](#common-commands)

## Current Layout

| Marker | Path | Purpose |
| --- | --- | --- |
| `unit` | `tests/unit/` | Isolated checkers, configuration, Make, and workflow contracts |
| `integration` | `tests/integration/` | CLI dispatch, checker results, and reporting |
| `meta` | `tests/meta/` | Built wheel and source-distribution contracts |
| `e2e` | `tests/e2e/` | Clean installations and installed CLI behavior |
| None | `tests/support/` | Shared fixtures; not collected as tests |

## Discovery and Selection

`make test` and plain pytest collect unit and integration tests only. Artifact tests remain opt-in
because building and installing distributions may access package indexes.

Selecting `tests/` explicitly collects all test layers. Marker filters operate only on the selected
paths; use `python -m pytest tests/meta -m meta` for the artifact layer. No CDK synthesis,
deployment, or cloud credentials are involved.

## Dependency Prerequisites

Install the project and development tools with `make dev PY=python3.13` (or `PY=python3.14`), or
install `-e '.[dev]'` in an active supported Python environment. Default tests do not require cloud
credentials or package-index access. Artifact tests may download build and installation
dependencies; see the [contributing guide] for isolated environments and dependency boundaries.

## Shared Fixtures

The root conftest registers [artifact fixtures] as a pytest plugin. Both artifact layers reuse one
wheel and one sdist per session, either from `--artifact-dir` or an isolated temporary build.
Artifacts pass `twine check` before their tests. Installation tests remove source-path overrides and
exercise the installed CLI outside the checkout.

Use the session-scoped `repository_root` fixture for project-level fixture needs. Keep fixtures at
the narrowest useful scope and put cross-layer helpers in `support/`. Do not add empty layers for
infrastructure or examples that this project does not have.

## Suite Design

Group related scenarios into plain pytest `Test*` classes with instance methods; use fixtures rather
than constructors or shared mutable class state. Parameterize inputs that share a contract and
assert specific diagnostics, not merely a nonempty result. The `write_file` fixture creates
temporary UTF-8 repository files. Keep domain-specific policy fixtures local to their test module.
Subprocess tests use timeouts; Make runs against a temporary copy of the Makefile, and Make and Git
fixtures exclude inherited tool configuration where it can change the result.

Installed-CLI scenarios share a module-scoped environment per artifact, but each consumer check gets
its own temporary project. Help and version checks exercise both the console script and module entry
point for each artifact. Coverage is diagnostic; no reduced threshold masks regressions.

## Common Commands

After installing development dependencies:

```console
make test
make test-unit
make test-integration
make test-distribution
make test-installation
make test-full
python -m pytest -m integration
python -m pytest tests/meta tests/e2e --artifact-dir dist
python -m pytest --cov=popo --cov-branch --cov-report=term-missing
```

See the [contributing guide] for setup and dependency prerequisites.

[artifact fixtures]: support/artifacts.py
[contributing guide]: ../CONTRIBUTING.md
