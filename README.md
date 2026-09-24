<!--
README.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Project overview, supported checks, setup, and documentation entry points.

Maintainer Notes
- Keep examples aligned with the CLI and configurable consumer policy.
- Keep local links and documented behavior consistent with repository sources.
- Keep badge targets aligned with package metadata and workflow filenames.
-->

# popo

[![Release][release badge]][GitHub releases]
[![Python][Python badge]][Python support]
[![License][license badge]][MIT License]
[![CI][CI badge]][CI workflow]
[![PR Gates][PR gates badge]][PR gates workflow]

Your project’s rules. Enforced.

`popo` is an extensible, read-only repository policy checker for software projects. It gives local
development, pre-commit hooks, and continuous integration (CI) the same commands and exit codes.

- [Getting Started](#getting-started)
- [At a Glance](#at-a-glance)
- [Release Status](#release-status)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Design Boundaries](#design-boundaries)
- [Development](#development)
- [PyPI Publication](#pypi-publication)
- [License](#license)
- [Contributing](#contributing)
- [Documentation](#documentation)
  - [User Documentation](#user-documentation)
  - [Contributor and Maintainer Docs](#contributor-and-maintainer-docs)

## Getting Started

- Review the supported toolchain in [Requirements](#requirements).
- Install a selected tag or local checkout as described in [Installation](#installation).
- Run a repository check with the [Quickstart](#quickstart).
- Adapt [Configuration](#configuration) to the repository being checked.
- Follow [Development](#development) to work on Popo itself.

## At a Glance

- Run the same checks locally, in pre-commit hooks, and in CI.
- Inspect the current repository or select another with `--root`.
- Configure consumer policy independently of Popo's own development settings.
- Validate repository files without modifying them or requiring cloud credentials.

## Release Status

Popo is a pre-1.0 package with alpha development status. Review the [changelog] and [release
archive] for compatibility changes and candidate status. The release badge reports Git tags; it does
not establish successful artifact publication. GitHub Release publication is opt-in, and PyPI
publishing is not configured; see the [release policy].

<a id="checks"></a>

## Features

- Local Markdown links and heading anchors;
- Immutable GitHub Actions references;
- Dependency metadata synchronized with requirements or constraints files;
- Python-version policy across package metadata, tool configuration, and workflows; and
- Dated semantic-version entries in a changelog.

## Requirements

- Python 3.13 or 3.14 (`.python-version` selects Python 3.13 for compatible local
  version managers).
- `packaging>=26.3,<27`, installed automatically with Popo; older versions are not supported.
- Make and a POSIX-compatible shell for the development targets; see the
  [contributing guide] for Windows setup.
- No cloud account or credentials are required to run repository checks.

## Installation

Choose an existing tag from [GitHub tags] and replace `vMAJOR.MINOR.PATCH` below with that tag.
Installing directly from Git requires Git on PATH:

```console
python -m pip install "popo @ git+https://github.com/Dagitali/popo.git@vMAJOR.MINOR.PATCH"
```

Install from a local checkout into your chosen Python environment:

```console
python -m pip install .
```

For an editable installation with development tools, see [Development](#development).

## Quickstart

Run a check from the repository it should inspect:

```console
popo check-docs
popo check-github-actions-pins
popo check-dependency-boundaries
popo check-python-policy
popo check-release-changelog v1.2.3
popo check-all
```

Every command accepts `--root`. The equivalent module entry point is
`python -m popo`.

`check-all` runs the documentation, action-pin, dependency, and Python-policy checks. Release
changelog validation is separate and requires the release version to check.

## Configuration

Configuration lives in the inspected repository's `pyproject.toml`. Paths are relative to the
repository root.

```toml
[tool.popo.dependencies]
metadata = "pyproject.toml"
requirements = "requirements/lowest.txt"
mode = "minimum-constraints"

[tool.popo.python-policy]
metadata = "pyproject.toml"
requires-python = ">=3.13,<3.15"
python-version = "3.13"
python-version-file = ".python-version"
ruff-config = "pyproject.toml"
ruff-target-version = "py313"
mypy-python-version = "3.13"
workflow-directory = ".github/workflows"
```

Dependency modes are:

- `minimum-constraints`: every runtime dependency must have a lower bound and matching
  `name==version` constraint.
- `exact`: project dependencies and installer requirements must be semantically identical.

When dependency configuration is absent, `popo` detects the layouts
`pyproject.toml` plus `requirements/lowest.txt`, root `requirements.txt`, or
`infra/pyproject.toml` plus `infra/requirements.txt`.

<a id="safety"></a>

## Design Boundaries

All checks are read-only. `popo` does not deploy infrastructure, modify repositories, or contact
GitHub. The Markdown checker validates repository-local links only.

Consumer projects own their policy choices, branching model, and deployment lifecycle. Python- and
GitHub-specific checks are available, but the tool does not require a particular cloud platform.
Passing repository checks does not establish that hosted branch protections are enabled or that a
release has been published.

## Development

From the Popo checkout, create `.venv`, install development dependencies, and run the local quality
gate:

```console
make dev PY=python3.13
make check
```

Use `PY=python3.14` instead when developing with Python 3.14. Make selects the managed environment
when no virtual environment is active; activation is not required for `make test` or `make check`.
An explicit `PYTHON` override takes precedence.

Alternatively, activate your own supported Python environment and install in editable mode:

```console
python -m pip install -e '.[dev]'
make check
```

Run `make check` for lint, types, regression tests, and repository-policy checks. Use `make hooks`
to install optional pre-commit hooks and `make check-release` to also build and test the wheel and
source distribution in clean environments. See the [contributing guide] for Windows paths,
environment overrides, network requirements, and other setup and focused-check targets.

## PyPI Publication

No workflow currently publishes Popo to PyPI. Until publication is configured and a release is
available there, use the Git-tag or local-checkout installation paths above. After the first PyPI
release, the intended installation command is:

```console
python -m pip install popo
```

Publication requires a separately authorized release process; see the [release policy].

## License

This project is licensed under the [MIT License].

## Contributing

Code and documentation contributions are welcome. Follow the [contributing guide] for development,
testing, hooks, and pull-request expectations.

## Documentation

### User Documentation

- [Configuration](#configuration): Consumer repository settings and dependency modes.
- [Changelog]: Project change history.
- [Release archive]: Release-aligned scope, compatibility, and validation records.

### Contributor and Maintainer Docs

- [Contributing guide]: Development workflow, quality gates, and GitHub automation.
- [Test layout]: Test layers, selection, shared fixtures, and artifact boundaries.
- [Agent instructions]: Repository rules for automated coding agents.
- [Release policy]: Artifact validation and publication safeguards.

Release validation, opt-in GitHub publication, and disposable installation tests are documented in
the [release policy].

[Python support]: #requirements
[agent instructions]: AGENTS.md
[changelog]: CHANGELOG.md
[contributing guide]: CONTRIBUTING.md
[MIT License]: LICENSE
[release policy]: RELEASE-POLICY.md
[release archive]: docs/releases/README.md
[CI workflow]: https://github.com/Dagitali/popo/actions/workflows/ci.yml
[CI badge]: https://github.com/Dagitali/popo/actions/workflows/ci.yml/badge.svg?branch=main
[PR gates workflow]: https://github.com/Dagitali/popo/actions/workflows/pr.yml
[PR gates badge]: https://github.com/Dagitali/popo/actions/workflows/pr.yml/badge.svg?branch=main
[GitHub releases]: https://github.com/Dagitali/popo/releases
[GitHub tags]: https://github.com/Dagitali/popo/tags
[Python badge]: https://img.shields.io/badge/python-3.13%20%7C%203.14-blue.svg
[license badge]: https://img.shields.io/github/license/Dagitali/popo.svg
[release badge]: https://img.shields.io/github/v/tag/Dagitali/popo?label=release
[test layout]: tests/README.md
