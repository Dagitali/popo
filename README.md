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
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
  - [Automation Contracts](#automation-contracts)
- [Design Boundaries](#design-boundaries)
- [Development](#development)
- [Support Popo](#support-popo)
- [PyPI Publication](#pypi-publication)
- [License](#license)
- [Contributing](#contributing)
- [Documentation](#documentation)
  - [User Documentation](#user-documentation)
  - [Community Health](#community-health)
  - [Maintainer Docs](#maintainer-docs)

## Getting Started

To get started:

- Review the supported toolchain in [Requirements](#requirements).
- Install a selected tag or local checkout as described in [Installation](#installation).
- Run a repository check with the [Quickstart](#quickstart).
- Adapt [Configuration](#configuration) to the repository being checked.
- Follow [Development](#development) and [Developer onboarding] to work on Popo itself.

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

## Features

- Local Markdown inline links, reference definitions, and heading or explicit HTML anchors,
  excluding fenced code examples, rejecting repository-escaping targets, and limiting fragment
  validation to Markdown targets; generated and vendored sources such as `node_modules` are
  excluded;
- Named remote GitHub Actions references pinned to full commit SHAs;
- Configurable automation contracts for local workflows/actions, composite steps, and templates;
- Dependency metadata synchronized with requirements or constraints files, including commented pins;
- Python-version policy across package metadata, tool configuration, and workflows, including
  inline and block-list version matrices; and
- Dated semantic-version entries in a changelog.

Popo's PR workflow checks dated changelog entries against versioned release documents and validates
candidate versions on release/hotfix branches. Hosted required-check configuration is needed to
block merges; see [workflow map] for the validation boundary.

Test modules use scope prefixes (`test_u_`, `test_i_`, `test_e_`, and `test_m_`) to reduce
cross-layer namespace collisions; see [test layout] for discovery and selection.

## Architecture

Local commands, hooks, and CI invoke the same CLI. It selects the repository root, loads consumer
configuration for checks that need it, and dispatches to the relevant checker. Checkers inspect
repository files and return findings; shared reporting prints `PASS` or `FAIL` messages and returns
an exit status of `0` for a successful check or `1` for reported failures. Invalid command-line
arguments are handled separately by the argument parser.

Configuration models and loaders live in the `popo.config` subpackage, organized by dependency,
Python-policy, and automation settings. Existing `popo.config` imports remain available through
explicit package exports.

Keeping command dispatch, configuration, checks, and reporting separate allows reusable validation
without embedding a consumer's build or deployment process. See [Architecture] for component
ownership and [Design] for compatibility and evolution rules.

## Requirements

- Python 3.13 or 3.14 (`.python-version` selects Python 3.13 for compatible local
  version managers).
- `packaging>=26.3,<27`, installed automatically with Popo; older versions are not supported.
- `PyYAML>=6.0.3,<7`, installed automatically for automation-contract parsing.
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
popo check-automation-contracts
popo check-dependency-boundaries
popo check-python-policy
popo check-release-changelog v1.2.3
popo check-all
```

Every command accepts `--root`. The equivalent module entry point is
`python -m popo`.

`check-all` runs the documentation, action-pin, dependency, and Python-policy checks. Release
changelog validation is separate and requires the release version to check. Automation contracts are
included when the consumer explicitly configures `[tool.popo.automation]`.

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

### Automation Contracts

`popo check-automation-contracts --root .` validates parsed YAML, duplicate keys, local
workflow/action input contracts, composite-step structure, template metadata, and immutable remote
references. Use `--pins-only` to skip input, composite, and metadata checks; parsing and local
target resolution still run. The older `check-github-actions-pins` command is unchanged.

See the [automation settings reference] for command boundaries and validation rules. Configure
discovery and policy in the consuming repository, without importing Popo internals:

```toml
[tool.popo.automation]
workflow-globs = [".github/workflows/*.yml"]
action-globs = ["actions/*/action.yml"]
template-globs = ["workflow-templates/*.yml"]
yaml-globs = [".github/ISSUE_TEMPLATE/*.yml"]
local-repositories = ["example/automation"]
template-placeholder-refs = ["REPLACE_WITH_RELEASE_SHA"]
```

All settings are arrays of strings. Only `workflow-globs` has a nonempty default, as shown above;
other settings default to `[]`. Patterns are root-relative and must each match a file. Use `[]` to
disable a category. Add `.yaml` patterns if used by your repository. `yaml-globs` validates syntax
only. Invalid settings, unreadable files, and escaping paths fail validation.

Local `./` references and configured `owner/repository` aliases resolve against the current
checkout, never against historical or remote commits. Calls reject unknown/missing required inputs
and literal workflow input type mismatches; expression values are not evaluated. Composite actions
require names, descriptions, and nonempty steps with exactly one of `run` or `uses`; `run` steps
require shells. Templates require matching `.properties.json` files with names/descriptions and
valid optional categories/filePatterns; orphan metadata is reported.

Placeholder exemptions apply only to configured template files referencing existing targets through
a configured local alias. They never exempt ordinary workflows or third-party actions. Like the
existing pin checker, local and `docker://` references are exempt from SHA pinning. No commands are
executed, sources rewritten, or network requests made. Commit existence, container immutability,
expression evaluation, secrets, outputs, and the complete GitHub schema are outside this check;
retain actionlint and hosted tests. YAML mapping keys must be strings; `on` remains a string, while
only `true` and `false` are interpreted as booleans.

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

Unit tests group checker coverage under `tests/unit/checks/` and configuration coverage under
`tests/unit/configs/`. Independent parameterized scenarios and isolated subprocess fixtures keep
failures reproducible; see the [test layout] for selection and shared-fixture conventions.

When optional hooks are installed, the pre-push stage runs `make check-pre-push` (the full local
quality gate). It does not install dependencies, build distributions, or publish artifacts.

Alternatively, activate your own supported Python environment and install in editable mode:

```console
python -m pip install -e '.[dev]'
make check
```

Run `make check` for lint, types, regression tests, and repository-policy checks. Use `make hooks`
to install optional pre-commit hooks and `make check-release` to also build and test the wheel and
source distribution in clean environments. See the [contributing guide] for Windows paths,
environment overrides, network requirements, and other setup and focused-check targets.

## Support Popo

Help improve Popo through reproducible bug reports, small consumer examples, tests, documentation,
and reviewed contributions. Use the [support guide] for help and reporting details, the [security
policy] for vulnerabilities, and the [Code of Conduct] for participation standards.

The [roadmap] describes readiness considerations without promising delivery dates or new features.
Consumer adoption is useful evidence when it identifies reusable needs without exposing private
repository data.

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

Code and codeless contributions are welcome. Follow the [contributing guide] for development,
testing, documentation, hooks, and pull-request expectations. Reproducible bug reports, usage
feedback, and documentation corrections are useful contributions alongside code changes.

## Documentation

### User Documentation

- [Documentation index]: Guides, scope, and local documentation validation.
- [Configuration reference]: All consumer settings, defaults, and command boundaries.
- [API guidance]: Public interface boundaries and compatibility review.
- [Adoption playbook]: Introduce checks and migrate existing consumer policy with baseline evidence.
- [Architecture] and [Design]: Components, integration boundaries, and configuration-change review.
- [References]: Canonical sources, upstream tooling documentation, and format references.
- [Configuration](#configuration): Consumer repository settings and dependency modes.

### Community Health

- [Contributing guide]: Development workflow, quality gates, and GitHub automation.
- [Issue forms]: Structured bug reports, feature requests, and documentation corrections.
- [Code of Conduct]: Participation and moderation.
- [Security policy]: Sensitive reporting and validation limits.
- [Support guide]: Supported interfaces and versions, help channels, and useful report contents.

Do not include credentials, private repository data, or vulnerability details in public issues.

### Maintainer Docs

- [Developer onboarding]: First local checks, repository orientation, and CLI learning path.
- [Test layout]: Test layers, selection, shared fixtures, and artifact boundaries.
- [Testing guide]: Focused checks, dependency boundaries, and installation validation.
- [Agent instructions]: Repository rules for automated coding agents.
- [Workflow map]: CI/CD roles, triggers, and publication boundaries.
- [Learnings]: Test selection, dependency drift, action pins, package versions, and recovery.
- [Roadmap]: Current foundations and evidence needed for future scope decisions.
- [Branch protection]: Configurable PR routing, required checks, and hosted-setting boundaries.
- [Changelog]: Project change history.
- [Release archive]: Release-aligned scope, compatibility, and validation records.
- [Release policy]: Artifact validation and publication safeguards.
- [Release checklist]: Preparation, validation, and separately authorized tagging and publication.
- [Release playbook]: Evidence and closeout checklist for maintainers.

Release validation, opt-in GitHub publication, and disposable installation tests are documented in
the [release policy].

[Python support]: #requirements
[Branch protection]: .github/BRANCH-PROTECTION.md
[Issue forms]: .github/ISSUE_TEMPLATE/
[agent instructions]: AGENTS.md
[Architecture]: ARCHITECTURE.md
[changelog]: CHANGELOG.md
[Workflow map]: CI-CD-WORKFLOWS.md
[Code of Conduct]: CODE_OF_CONDUCT.md
[contributing guide]: CONTRIBUTING.md
[Release checklist]: CONTRIBUTING.md#release-preparation
[Design]: DESIGN.md
[Learnings]: LEARNINGS.md
[MIT License]: LICENSE
[References]: REFERENCES.md
[release policy]: RELEASE-POLICY.md
[roadmap]: ROADMAP.md
[security policy]: SECURITY.md
[support guide]: SUPPORT.md
[Configuration reference]: docs/CONFIGURATION.md
[automation settings reference]: docs/CONFIGURATION.md#automation-settings
[Documentation index]: docs/README.md
[Testing guide]: docs/TESTING.md
[API guidance]: docs/api/README.md
[Developer onboarding]: docs/development/onboarding.md
[Adoption playbook]: docs/playbooks/adopt-popo.md
[Release playbook]: docs/playbooks/release.md
[release archive]: docs/releases/README.md
[CI workflow]: https://github.com/Dagitali/popo/actions/workflows/ci.yml
[CI badge]: https://github.com/Dagitali/popo/actions/workflows/ci.yml/badge.svg?branch=main
[PR gates workflow]: https://github.com/Dagitali/popo/actions/workflows/pr.yml
[PR gates badge]: https://github.com/Dagitali/popo/actions/workflows/pr.yml/badge.svg
[GitHub releases]: https://github.com/Dagitali/popo/releases
[GitHub tags]: https://github.com/Dagitali/popo/tags
[Python badge]: https://img.shields.io/badge/python-3.13%20%7C%203.14-blue.svg
[license badge]: https://img.shields.io/github/license/Dagitali/popo.svg
[release badge]: https://img.shields.io/github/v/tag/Dagitali/popo?label=release
[test layout]: tests/README.md

[workflow map]: CI-CD-WORKFLOWS.md
