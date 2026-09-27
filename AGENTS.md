<!--
AGENTS.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Repository boundaries, development conventions, and agent validation duties.

Maintainer Notes
- Preserve read-only checks and require authorization for external operations.
- Keep local links and documented behavior consistent with repository sources.
-->

# AGENTS

These instructions apply to automated coding agents working in this repository.

- [Repository Boundaries](#repository-boundaries)
- [Agent Operating Model](#agent-operating-model)
- [Development Policy](#development-policy)
- [Documentation Obligations](#documentation-obligations)
- [Validation Commands](#validation-commands)
- [Validation and Completion](#validation-and-completion)

## Repository Boundaries

- Treat `pyproject.toml` as the canonical package and tool configuration.
- Derive distribution versions from Git tags through `setuptools-scm`; do not introduce a second
  release-version source or treat source-import fallback values as release evidence.
- Preserve the `src/` layout and intentional package-root `__all__` exports. Internal checker
  modules are not a promised consumer API; prefer the public CLI in adoption examples.
- Keep checks read-only: commands may inspect repositories but must not modify them.
- Keep generic checking logic separate from any one consumer repository's policy.

## Agent Operating Model

- Read the applicable instructions and inspect `git status --short` before editing.
- Preserve unrelated changes, staged work, and user-owned files; do not stage or commit implicitly.
- Trace commands to the Makefile, package configuration to `pyproject.toml`, and automation claims
  to the relevant workflow. State assumptions rather than inventing repository behavior.
- Keep generated builds, caches, virtual environments, and package metadata out of source edits.
- Keep changes focused and explain any necessary expansion of scope.

## Development Policy

- Add or update tests whenever command behavior or configuration changes.
- Organize tests by unit, integration, meta, and e2e scope; keep shared fixtures in tests/support.
  Default checks run unit and integration tests; artifact layers are opt-in.
- Use single-quoted Python strings, an 88-character line length, and strict typing.
- Use NumPy-style public docstrings with meaningful parameter, return, and exception contracts.
  Document caught errors returned as diagnostics separately from exceptions that propagate.
- Keep unit tests deterministic and independent of credentials, deployed services, and network
  access; isolate network-dependent artifact work in the explicit distribution/installation layers.
- Keep remote GitHub Actions pinned to full commit SHAs and preserve least-privilege permissions.
- Keep supported Python versions aligned with `project.requires-python` and the repository's
  Python-policy checks; do not couple consumer checks to Popo's own development configuration.

## Documentation Obligations

- Follow the [documentation synchronization guide] to identify canonical sources and affected
  documents; prefer links over duplicating detailed guidance.
- Preserve purposeful consumer-policy differences instead of copying another project's tooling,
  cloud assumptions, or release commitments.
- Keep file header comments accurate and use bottom-of-document reference links sorted by
  destination, as specified in the contributing guide.
- Documentation work does not authorize changing implementation, workflow permissions, hosted
  settings, or release behavior. Report discrepancies that require a separate implementation task.

## Validation Commands

Use Make targets as the stable contributor interface. Select focused checks by the changed boundary,
then run the default quality gate when practical:

| Change | Minimum focused validation |
| --- | --- |
| Python checker or configuration | `make lint typecheck test-unit` |
| CLI dispatch, arguments, reporting, or exit codes | `make test-unit test-integration` |
| Workflow or composite action | `make github-actions-pins python-policy test-unit` |
| Dependencies or package metadata | `make dependency-policy test-distribution` |
| Artifact fixtures, builds, or installed entry points | `make test-distribution test-installation` |
| Markdown documentation | `make docs-markdown` |
| Release candidate | `make release-changelog RELEASE_VERSION=vMAJOR.MINOR.PATCH` and `make check-release` |

`make check` covers lint, formatting, typing, unit/integration tests, and repository policy. It does
not build distributions or exercise clean installations. Changes to shared artifact fixtures must
also exercise their build-on-demand path without supplying `--artifact-dir`; the focused
distribution and installation targets do this by default. A passing prebuilt-artifact test does not
validate artifact creation.

Artifact checks may download dependencies and use temporary environments; they do not publish. For
release validation, use a fresh `PYTHON_DIST_DIR` rather than deleting unrelated artifacts, and
follow the [release playbook]. Local results do not establish hosted cross-platform success. See the
[testing guide] for test selection and the [test layout] for fixture conventions.

## Validation and Completion

- Run `make check` before completion when practical.
- For Markdown changes, run `make docs-markdown` to check local targets and heading anchors;
  separately verify factual claims against their source files.
- Update `README.md` and `CHANGELOG.md` for user-visible changes.
- Do not publish packages, create release tags, or mutate external repositories without explicit
  authorization.

Use focused tests while iterating, then the applicable quality gate. Report files changed,
intentional differences preserved, checks run, failures, and checks skipped with their reasons.
Never claim success from edits alone or weaken a check to hide a failure.

See the [contributing guide], [test layout], and [release policy] for command and artifact details.

[contributing guide]: CONTRIBUTING.md
[documentation synchronization guide]: CONTRIBUTING.md#documentation-synchronization
[release policy]: RELEASE-POLICY.md
[testing guide]: docs/TESTING.md
[release playbook]: docs/playbooks/release.md
[test layout]: tests/README.md
