<!--
CONTRIBUTING.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Contributor setup, validation, packaging, and review workflow.

Maintainer Notes
- Keep commands synchronized with Make and avoid private or local-only references.
- Keep local links and documented behavior consistent with repository sources.
-->

# Contributing Guidelines

Contributions to code, tests, documentation, and repository automation are welcome. Contributions
are distributed under the project's [MIT License].

- [Ways to Contribute](#ways-to-contribute)
- [Development Workflow](#development-workflow)
- [Development Setup](#development-setup)
- [Public API and Type Checking](#public-api-and-type-checking)
- [Local Checks And Hooks](#local-checks-and-hooks)
- [Distribution Validation](#distribution-validation)
- [Documentation](#documentation)
  - [Documentation Synchronization](#documentation-synchronization)
- [GitHub Automation](#github-automation)

## Ways to Contribute

Useful contributions include reproducible bug reports, focused feature proposals, compatibility
tests, documentation corrections, and packaging or automation improvements. Discuss substantial
changes before implementing them. Do not include credentials or private repository data in issues.

## Development Workflow

1. Create a focused topic branch from the appropriate integration branch.
2. Install development dependencies and optionally install hooks with `make hooks`.
3. Implement one cohesive change with relevant tests and documentation.
4. Run `make check` and address failures rather than weakening validation.
5. Update the [changelog] for user-visible behavior and open a pull request.
6. Follow the repository's configured review, branch-protection, and PR-routing requirements.

Versions come from Git tags through `setuptools-scm`; do not introduce another version source.
Review the [release policy] for packaging or release changes. Popo's routing is configurable: the
[branch-protection guide] describes optional policies, not proof of active hosted settings.

## Development Setup

Create and activate a virtual environment with Python 3.13 or 3.14, then install the project in
editable mode:

```console
python -m pip install -e '.[dev]'
make check
```

Use focused tests while iterating. Add an `Unreleased` changelog entry for user-visible changes.
Commits should use Conventional Commits.

Alternatively, run `make dev PY=python3.13` (or `PY=python3.14`) to create `.venv` and install the
development extras. `make setup` aliases `dev`; `make install` installs only the runtime project,
and `make venv` creates the environment without installing the project. `make show-venv` reports the
selected paths without creating anything. Override `VENV_DIR` to choose a dedicated directory.
Existing environments are reused only when their Python major/minor version matches `PY`; mismatches
and unusable paths fail without replacing them. Explicit installation targets may access the
network.

Setup does not activate the environment. Make honors an explicit `PYTHON` override, then an
activated virtual environment's `python3`, then the managed environment's interpreter when present,
and otherwise `python3` on PATH. After `make dev`, plain `make test` and `make check` work without
activation or `PYTHONPATH` overrides. Pytest includes `src` on its import path, and Make prepends
this checkout's `src` to `PYTHONPATH`. Distribution installation tests remove that override before
testing installed packages outside the checkout. The Windows Make targets require a POSIX-compatible
shell and Make, such as Git Bash.

## Public API and Type Checking

Keep reusable checks independent of any one consumer's repository layout, programming language, or
cloud platform. Review commands, flags, configuration, diagnostics, and exit codes when changing
public behavior. Add regression tests for compatibility and error handling, and retain read-only
operation. Keep type annotations explicit and validate them with `make typecheck`.

## Local Checks And Hooks

`make check` runs Ruff, mypy, the default regression suite, and popo's own repository checks. `make
self-check` runs just the repository checks. The default suite does not build distributions or
install dependencies from the network.

Tests follow the [test layout]: `unit/` covers isolated checks and automation contracts,
`integration/` covers CLI dispatch and reporting, `meta/` covers built artifacts, and `e2e/` covers
clean installations. Shared artifact fixtures live in `support/`. Default discovery includes only
unit and integration tests. Use `make test-unit` or `make test-integration` for a focused layer;
root conftest assigns matching pytest markers.

Run `make help` to list available targets. Plain `make` still runs `check`. Focused policy targets
are `python-policy`, `dependency-policy`, `github-actions-pins`, and `docs-markdown`. Use
`release-changelog RELEASE_VERSION=x.y.z` for a dated release entry. `format-check` is read-only;
`fix` applies Ruff fixes, while `fmt` aliases the existing `format` target. `lint` continues to
check both lint and formatting.

Override `PYTHON` to select an interpreter; tool commands such as `RUFF` and `PYTEST` are also
overridable. Pass focused pytest options with `TEST_ARGS`, for example:

```console
make test TEST_ARGS='-k changelog'
```

Ordinary checks do not create environments or implicitly install development dependencies; only
explicit setup targets do so.

Run `make hooks` to opt into pre-commit hooks. The Popo hook uses `make self-check`, including
Make's interpreter selection and source-path handling. The Ruff hooks use a pre-commit-managed
Python environment and retain filename-based checks. Their dependency range matches the development
extra in `pyproject.toml`. The first hook run downloads the upstream hook environment. Run all hooks
manually with `python -m pre_commit run --all-files`.

## Distribution Validation

- `make dist` builds a wheel and source distribution and runs `twine check`.
- `make test-distribution` builds fresh temporary artifacts and checks their contents.
- `make test-installation` builds fresh temporary artifacts and installs each in a clean virtual
  environment, then exercises the CLI outside the checkout.
- `make check-release` runs all checks against the artifacts in `dist/`.

`make build` aliases `dist`; `make test-full` runs the default suite plus both distribution suites.
`make check-pre-push` aliases the existing local quality gate. Override `PYTHON_DIST_DIR` to change
the build and release-validation artifact directory. These local targets do not replace CI's
multi-platform and dependency-boundary matrices.

The Makefile also exposes `DIST_BUILD_COMMAND` and `DIST_CHECK_COMMAND` for alternative packaging
commands. `DISTRIBUTION_TEST_PATH` and `INSTALLATION_TEST_PATH` select the standalone test files;
their corresponding `DISTRIBUTION_TEST_ARGS` and `INSTALLATION_TEST_ARGS` default to `TEST_ARGS`
plus the selected path. Overriding a complete argument variable replaces that default, so include
the intended test path. The release gate still tests both artifact layers against the same built
artifacts.

Distribution checks require network access for build and installation dependencies. When reusing
artifacts, provide a directory containing exactly one wheel and one source distribution:

```console
python -m pytest tests/meta tests/e2e --artifact-dir dist
```

Move stale artifacts out of `dist/` before building a new version. CI builds once and tests those
same artifacts on each supported Python version. None of these commands publishes a package or
creates a release.

## Documentation

Document public behavior and decision-relevant constraints rather than restating implementation line
by line. Use descriptive link text, repository-relative links for local documents, and backticks for
commands, paths, and identifiers. Keep headings and table-of-contents entries synchronized.

Update public usage, configuration, tests, and release notes when their source of truth changes.
Keep documentation language- and platform-neutral where the behavior is reusable. Use reference
links for shared destinations, and run `make docs-markdown` to validate local targets and anchors.
Do not link public guidance to private notes, local-only files, or generated build output.

Keep reference-link definitions together at the bottom of each document. Sort them
lexicographically by destination URL or path exactly as written (case-sensitive), then by label
as a tie-breaker. Preserve destination casing, fragments, and encoding; do not normalize URLs
or rewrite labels merely to sort them. This convention applies to anchors, relative paths,
and external URLs alike.

### Documentation Synchronization

Verify claims against executable sources before updating the maintained guides:

| Claim | Source of truth | Documentation to review |
| --- | --- | --- |
| Package metadata, dependencies, Python support | `pyproject.toml` | [README], this guide, [test layout] |
| Contributor commands and environment selection | `Makefile` | [README], this guide, [agent instructions], [test layout] |
| CLI behavior, configuration, diagnostics, exit codes | `src/popo/cli.py`, `src/popo/config.py`, check implementations and tests | [README], [changelog] |
| Test layers, fixtures, and selection | `tests/conftest.py`, `tests/support/`, pytest configuration | [test layout], this guide, [agent instructions] |
| Workflow triggers, checks, permissions, artifacts | `.github/workflows/`, setup action | [branch-protection guide], this guide, [release policy] |
| Versioning and release validation | `pyproject.toml`, `Makefile`, CD workflow | [release policy], [release notes template], [changelog] |

Search for references to a changed command or behavior, then update the smallest set of affected
guides. Link to existing explanations instead of creating competing copies. Run `make docs-markdown`
and inspect the diff for stale project names, private data, and unsupported claims. This validates
local links and anchors, not external URL availability or factual accuracy.

Documentation-only work must not change code, workflow permissions, repository settings, or release
behavior merely to make prose accurate. Report conflicting evidence and request a separate change
when resolving it requires implementation or external operations. Workflow files describe intended
automation; they do not prove hosted protections or environments are configured.

## GitHub Automation

The [CI workflow] defines routine validation; the [release policy] describes artifact validation and
optional publication. CI uses the [Python setup action] and validates dependency integrity before
checks. Workflow changes should pass `actionlint` as well as `make check`.

CI additionally tests lowest/newest runtime dependency boundaries on Python 3.13 and 3.14, reports
branch coverage, and tests both distributions on macOS and Windows. To exercise dependency
boundaries locally, use separate disposable virtual environments: install `-e '.[dev]'` with
`--constraint requirements/lowest.txt` for lowest, or `--upgrade --upgrade-strategy eager` for
newest, then run `python -m pip check` and `python -m pytest`. Report package line and branch
coverage with:

```console
python -m pytest --cov=popo --cov-branch --cov-report=term-missing
```

The [SBOM workflow] and [security workflow] define supplementary inventory generation and manual
dependency auditing. They require network access and do not publish releases.

PR routing is configurable rather than tied to GitFlow. See the [branch-protection guide].
For tagged artifact validation, optional GitHub publication,
and manual disposable installations, see the [release policy]. No PyPI publishing
or cloud deployment is configured.

[branch-protection guide]: .github/BRANCH-PROTECTION.md
[release notes template]: .github/RELEASE-NOTES-TEMPLATE.md
[Python setup action]: .github/actions/setup-python-project/action.yml
[CI workflow]: .github/workflows/ci.yml
[SBOM workflow]: .github/workflows/sbom.yml
[security workflow]: .github/workflows/security.yml
[agent instructions]: AGENTS.md
[changelog]: CHANGELOG.md
[MIT License]: LICENSE
[README]: README.md
[release policy]: RELEASE-POLICY.md
[test layout]: tests/README.md
