<!--
README.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Project overview, supported checks, setup, and documentation entry points.

Maintainer Notes
- Keep examples aligned with the CLI and configurable consumer policy.
- Keep local links and documented behavior consistent with repository sources.
-->

# popo

Your project’s rules. Enforced.

`popo` is an extensible, read-only repository policy checker for software projects. It gives local
development, pre-commit hooks, and continuous integration (CI) the same commands and exit codes.

- [Getting Started](#getting-started)
- [Checks](#checks)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Safety](#safety)
- [Development](#development)
- [Contributing](#contributing)
- [Documentation](#documentation)
- [License](#license)

## Getting Started

- Review the supported toolchain in [Requirements](#requirements).
- Install from a local checkout as described in [Installation](#installation).
- Run a repository check with the [Quickstart](#quickstart).
- Adapt [Configuration](#configuration) to the repository being checked.
- Follow [Development](#development) to work on Popo itself.

## Checks

- Local Markdown links and heading anchors;
- Immutable GitHub Actions references;
- Dependency metadata synchronized with requirements or constraints files;
- Python-version policy across package metadata, tool configuration, and workflows; and
- Dated semantic-version entries in a changelog.

## Requirements

- Python 3.13 or 3.14 (`.python-version` selects Python 3.13 for compatible local
  version managers).
- Make and a POSIX-compatible shell for the development targets; see the
  [contributing guide] for Windows setup.
- No cloud account or credentials are required to run repository checks.

## Installation

Install from a local checkout into your chosen Python environment:

```console
python -m pip install .
```

After the first PyPI release:

```console
python -m pip install popo
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

## Safety

All checks are read-only. `popo` does not deploy infrastructure, modify repositories, or contact
GitHub. The Markdown checker validates repository-local links only.

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

## Contributing

Code and documentation contributions are welcome. Follow the [contributing guide] for development,
testing, hooks, and pull-request expectations.

## Documentation

- [Configuration](#configuration): Consumer repository settings and dependency modes.
- [Contributing guide]: Development workflow, quality gates, and GitHub automation.
- [Test layout]: Test layers, selection, shared fixtures, and artifact boundaries.
- [Agent instructions]: Repository rules for automated coding agents.
- [Changelog]: Project change history.
- [Release policy]: Artifact validation and publication safeguards.
- [Release archive]: Release-aligned scope, compatibility, and validation records.

Release validation, opt-in GitHub publication, and disposable installation tests are documented in
the [release policy].

## License

This project is licensed under the [MIT License].

[agent instructions]: AGENTS.md
[changelog]: CHANGELOG.md
[contributing guide]: CONTRIBUTING.md
[MIT License]: LICENSE
[release policy]: RELEASE-POLICY.md
[release archive]: release/README.md
[test layout]: tests/README.md
