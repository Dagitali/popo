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
- [Validation and Completion](#validation-and-completion)

## Repository Boundaries

- Treat `pyproject.toml` as the canonical package and tool configuration.
- Preserve the `src/` layout and keep the public API intentionally small.
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
- Keep supported Python versions aligned with `project.requires-python` and the repository's
  Python-policy checks; do not couple consumer checks to Popo's own development configuration.

## Validation and Completion

- Run `make check` before completion when practical.
- Update `README.md` and `CHANGELOG.md` for user-visible changes.
- Do not publish packages, create release tags, or mutate external repositories without explicit
  authorization.

Use focused tests while iterating, then the applicable quality gate. Report files changed,
intentional differences preserved, checks run, failures, and checks skipped with their reasons.
Never claim success from edits alone or weaken a check to hide a failure.

See the [contributing guide], [test layout], and [release policy] for command and artifact details.

[contributing guide]: CONTRIBUTING.md
[release policy]: RELEASE-POLICY.md
[test layout]: tests/README.md
