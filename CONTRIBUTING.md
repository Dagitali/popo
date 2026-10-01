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

Contributions to source code, tests, documentation, and repository automation are welcome through
GitHub issues and pull requests. By submitting a contribution, you agree that it may be distributed
under this project's [MIT License].

- [Ways to Contribute](#ways-to-contribute)
- [Development Workflow](#development-workflow)
  - [Development Setup](#development-setup)
- [Protected Branches and PR Routing](#protected-branches-and-pr-routing)
- [Public API and Type Checking](#public-api-and-type-checking)
- [Local Quality Gates](#local-quality-gates)
  - [GitHub Automation](#github-automation)
- [Testing](#testing)
  - [Distribution Validation](#distribution-validation)
  - [Release Preparation](#release-preparation)
- [Documentation](#documentation)
  - [Documentation Synchronization](#documentation-synchronization)
- [Community Standards](#community-standards)

## Ways to Contribute

Useful contributions include:

- reproducible bug reports with version and environment details;
- focused feature proposals that explain the underlying need;
- tests for public behavior and compatibility contracts;
- documentation corrections, examples, and accessibility improvements; and
- code, packaging, security, or automation improvements.

Discuss substantial changes in an issue before investing in an implementation.

## Development Workflow

1. Create a focused topic branch from the appropriate integration branch.
2. Install development dependencies and optionally install hooks with `make hooks`.
3. Implement one cohesive change, including tests and documentation when applicable.
4. Run `make check` and address failures rather than weakening the checks.
5. Update the [changelog] for user-visible behavior.
6. Push the branch and open a pull request using the [pull request template].
7. Merge through GitHub after the configured checks and reviews pass.

Package versions are derived from Git tags by `setuptools-scm`; do not add or hand-edit a second
version source. See the [release policy] and [release archive] for release-affecting changes.

### Development Setup

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

## Protected Branches and PR Routing

Popo's routing is configurable rather than tied to GitFlow. With `PR_TARGET_RULES` unset, the PR
gate imposes no target-branch restrictions. Follow the configured branch roles and required checks
described in the [branch-protection guide]; that guide is a proposed baseline, not proof that hosted
protections are active.

Do not treat local merge or branch-finishing commands, including `git flow ... finish`, as the
authoritative integration step: they bypass the pull-request review surface. Synchronize maintained
branches through reviewed pull requests. Do not assume `develop`, fixed source-branch prefixes, or a
support-branch strategy are required when no such policy has been configured.

## Public API and Type Checking

Keep reusable checks independent of any one consumer's repository layout, programming language, or
cloud platform. Review commands, flags, configuration, diagnostics, and exit codes when changing
public behavior. Add regression tests for compatibility and error handling, and retain read-only
operation. Names exported through the package root's `__all__` form its intentional package-level
public API; do not treat internal checker modules as a promised consumer API.

The package ships a `py.typed` marker and runs mypy in strict mode. When contributing Python code:

- Use syntax supported by the minimum Python version declared in `pyproject.toml`;
- Prefer precise boundary types over `Any` and explain unavoidable dynamic boundaries;
- Keep runtime validation for configuration rules that type checking cannot enforce;
- Avoid importing internal modules in examples when the public CLI is sufficient; and
- Add contract tests when changing public commands or configuration.

Run `make typecheck` locally and include migration guidance for intentional breaking changes.

## Local Quality Gates

`make check` runs Ruff, mypy, the default regression suite, and popo's own repository checks. `make
self-check` runs just the repository checks. The default suite does not build distributions or
install dependencies from the network.

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

The pre-push stage runs `make check-pre-push`, which delegates to the full local `make check` gate
without building distributions or installing tools. Run it directly, or exercise the hook with
`python -m pre_commit run make-check-pre-push --hook-stage pre-push --all-files`. The default manual
hook command above selects pre-commit hooks, not the pre-push stage. Local hooks provide early
feedback and do not replace hosted required checks.

### GitHub Automation

Dependabot may propose updates to `requirements/lowest.txt`, the minimum-version test fixture.
Before merging an accepted pin increase, raise the corresponding `pyproject.toml` lower bound to
match and document the dropped support for older versions. Dependabot may not update both files
together; complete that alignment in the same pull request. Run `make dependency-policy` and the
lowest-dependency tests. CI must continue rejecting mismatched pins and metadata; do not weaken the
consistency check to accept an update.

The [workflow map] describes automation roles and triggers. The [CI workflow] defines routine
validation; the [release policy] describes artifact validation and optional publication. CI uses the
[Python setup action] and validates dependency integrity before checks. Workflow changes should pass
`actionlint` as well as `make check`.

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

For tagged artifact validation, optional GitHub publication,
and manual disposable installations, see the [release policy]. No PyPI publishing
or cloud deployment is configured.

## Testing

Add tests for observable behavior and validation failures. Prefer public CLI behavior and stable
diagnostics over incidental implementation details. Unit tests must not require cloud credentials or
network access. Keep artifact installations and optional network-dependent checks separate from the
default deterministic suite.

Tests follow the [test layout]: `unit/` covers isolated checks and automation contracts,
`integration/` covers CLI dispatch and reporting, `meta/` covers built artifacts, and `e2e/` covers
clean installations. Shared artifact fixtures live in `support/`. Default discovery includes only
unit and integration tests. Use `make test-unit` or `make test-integration` for a focused layer;
`tests/conftest.py` assigns matching pytest markers.

### Distribution Validation

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

### Release Preparation

1. Review changes since the previous tag, including pending changes intended for the candidate. Keep
   dependency pins and metadata lower bounds synchronized; do not disable their CI check.
2. Move candidate changes from `Unreleased` into a dated `## [MAJOR.MINOR.PATCH] - YYYY-MM-DD`
   changelog section, leaving `Unreleased` available for subsequent changes.
3. Create `docs/releases/vMAJOR.MINOR.PATCH.md` from the [release notes template] and update the
   [release archive]. Mark the record planned until the release is finalized, and identify any
   compatibility changes and outstanding validation. The PR release-record gate requires the
   candidate's dated entry on release/hotfix branches and rechecks versioned documents for all dated
   entries. Feature work may stay under `Unreleased`.
4. Run `make release-changelog RELEASE_VERSION=vMAJOR.MINOR.PATCH`, `make docs-markdown`, and `make
   check-release`. Use a fresh `PYTHON_DIST_DIR` if existing artifacts belong to another build.
5. Review the final diff and record validation against the exact candidate checkout without
   embedding its commit SHA in Markdown. Development builds do not prove the eventual tag's version
   or artifacts; complete hosted checks separately.
6. Follow the [release policy] for separately authorized tagging and optional publication. Never
   move a released tag or treat documentation preparation as authorization to publish.

## Documentation

Keep prose concise, use descriptive link text, and wrap code, file names, commands, and identifiers
in backticks. Update nearby examples and cross-references when behavior or public interfaces change.
Prefer repository-relative links for local documents and authoritative primary sources for external
technical references.

Document public behavior and decision-relevant constraints rather than restating implementation line
by line. Keep headings in title case, preserve the official capitalization of tools and products,
and keep table-of-contents labels synchronized with their headings.

Update public usage, configuration, tests, and release notes when their source of truth changes.
Keep documentation language- and platform-neutral where the behavior is reusable. Use reference
links for shared destinations, and run `make docs-markdown` to validate local targets and anchors.
Do not link public guidance to private notes, local-only files, or generated build output.

Maintain release-aligned records under `docs/releases/` using the [release archive] and [release
notes template]. Keep planned candidates distinct from tagged versions and publication results;
update the archive index when adding a record.

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
| CLI behavior, configuration, diagnostics, exit codes | `src/popo/cli.py`, `src/popo/config/`, check implementations and tests | [README], [changelog] |
| Test layers, fixtures, and selection | `tests/conftest.py`, `tests/support/`, pytest configuration | [test layout], this guide, [agent instructions] |
| Workflow triggers, checks, permissions, artifacts | `.github/workflows/`, setup action | [branch-protection guide], this guide, [release policy] |
| Versioning and release validation | `pyproject.toml`, `Makefile`, CD workflow | [release policy], [release notes template], [changelog] |
| Component ownership and design constraints | CLI, configuration, validators, tests | [architecture], [design guidance] |
| Workflow roles and operational lessons | Workflow YAML, tests, incident evidence | [workflow map], [learnings] |
| Help channels and compatibility expectations | Maintainer decisions and public interface contracts | [support guide], [security policy], [Code of Conduct] |

Search for references to a changed command or behavior, then update the smallest set of affected
guides. Link to existing explanations instead of creating competing copies. Run `make docs-markdown`
and inspect the diff for stale project names, private data, and unsupported claims. This validates
local links and anchors, not external URL availability or factual accuracy.

Documentation-only work must not change code, workflow permissions, repository settings, or release
behavior merely to make prose accurate. Report conflicting evidence and request a separate change
when resolving it requires implementation or external operations. Workflow files describe intended
automation; they do not prove hosted protections or environments are configured.

## Community Standards

Follow the [Code of Conduct] in project spaces. Use the public [issue forms] for bugs, feature
requests, and documentation corrections; the [support guide] explains what to include. Follow the
[security policy] for sensitive vulnerability reports. Do not include credentials, private
repository data, or vulnerability details in public issues.

[branch-protection guide]: .github/BRANCH-PROTECTION.md
[issue forms]: .github/ISSUE_TEMPLATE/
[release notes template]: .github/RELEASE-NOTES-TEMPLATE.md
[Python setup action]: .github/actions/setup-python-project/action.yml
[pull request template]: .github/pull_request_template.md
[CI workflow]: .github/workflows/ci.yml
[SBOM workflow]: .github/workflows/sbom.yml
[security workflow]: .github/workflows/security.yml
[agent instructions]: AGENTS.md
[architecture]: ARCHITECTURE.md
[changelog]: CHANGELOG.md
[workflow map]: CI-CD-WORKFLOWS.md
[Code of Conduct]: CODE_OF_CONDUCT.md
[design guidance]: DESIGN.md
[learnings]: LEARNINGS.md
[MIT License]: LICENSE
[README]: README.md
[release policy]: RELEASE-POLICY.md
[security policy]: SECURITY.md
[support guide]: SUPPORT.md
[release archive]: docs/releases/README.md
[test layout]: tests/README.md
