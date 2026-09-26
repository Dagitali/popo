<!--
onboarding.md
popo/docs/development

Copyright © 2026 Dagitali LLC. All rights reserved.

First local session, repository orientation, and safe contributor workflow.

Maintainer Notes
- Keep setup commands aligned with Make; hooks do not install development dependencies.
- Link to canonical contributor guidance for environment and review policy.
-->

# Developer Onboarding

- [Prerequisites](#prerequisites)
- [First Local Session](#first-local-session)
- [Learn the Repository](#learn-the-repository)
- [Safe CLI Learning Path](#safe-cli-learning-path)
- [Pull Request Expectations](#pull-request-expectations)

## Prerequisites

Use Git, Make, a POSIX-compatible shell, and a Python version allowed by `pyproject.toml`. The
[development setup] explains supported interpreters, Windows requirements, and environment
selection. No cloud account or credentials are needed. Dependency installation may use the network;
normal unit and integration tests do not need package-index access.

## First Local Session

From the Popo checkout:

```console
git status --short
make dev PY=python3.13
make show-venv
make check
```

Use `PY=python3.14` for the other supported interpreter. Setup creates the managed environment and
installs development tools; it does not activate it. Make selects that environment when appropriate
without requiring activation. Existing mismatched environments are not replaced automatically.

Run `make hooks` after setup if you want local Git hooks. It is optional and separate from
dependency installation. Use `make help` to discover focused targets.

## Learn the Repository

1. Read the [agent instructions] and [contributing guide] before changing files.
2. Find the relevant maintained guide in the [documentation index].
3. Follow CLI dispatch in `src/popo/cli.py`, configuration in `src/popo/config.py`, individual
   validators in `src/popo/checks/`, and reporting in `src/popo/support.py`.
4. Read the matching unit and CLI integration tests alongside the implementation; see the [tests
   overview] for layer and fixture ownership.
5. Preserve unrelated working-tree changes and record the validation commands actually run.

Useful focused loops are `make test-unit`, `make test-integration`, and `make docs-markdown`. Use
the [testing guide] to select opt-in artifact tests for packaging changes.

## Safe CLI Learning Path

Start with `make self-check` against the checkout. For a consumer repository, use an installed CLI
and an explicit root, for example `popo check-docs --root /path/to/consumer`. Read the
[configuration reference] before enabling Python-specific policy checks; consumer settings are not
required to copy Popo's own policy.

Checks inspect files without fixing them. A failed check is evidence to review, not permission to
rewrite a consumer's configuration or disable CI gates. Do not include private repository content or
credentials in reports, and do not publish, tag, or change hosted settings as a learning step.

## Pull Request Expectations

Follow the configured branch and review policy in the [contributing guide]. Explain the scope,
compatibility effects, tests, documentation updates, and publication impact. Keep public commands,
configuration, diagnostics, and exit codes intentional. Use the [incident runbook] when a failure
requires diagnosis rather than routine implementation.

[agent instructions]: ../../AGENTS.md
[contributing guide]: ../../CONTRIBUTING.md
[development setup]: ../../CONTRIBUTING.md#development-setup
[tests overview]: ../../tests/README.md
[configuration reference]: ../CONFIGURATION.md
[documentation index]: ../README.md
[testing guide]: ../TESTING.md
[incident runbook]: ../runbooks/incident-response.md
