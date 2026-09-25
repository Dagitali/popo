<!--
CONFIGURATION.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Consumer configuration fields, defaults, and command boundaries.

Maintainer Notes
- Verify defaults against src/popo/config.py and command flags against src/popo/cli.py.
- Keep consumer policy separate from Popo's supported runtime and development settings.
-->

# Configuration Reference

Popo reads `[tool.popo]` from `pyproject.toml` in the inspected repository root. Select that root
with a command's `--root` option; otherwise it uses the working directory. Relative configured paths
are resolved against that root. See the [configuration example] for a complete starting point.

- [Dependency Settings](#dependency-settings)
- [Python-Policy Settings](#python-policy-settings)
- [Command Boundaries](#command-boundaries)
- [Validation Rules](#validation-rules)

## Dependency Settings

`[tool.popo.dependencies]` supports:

| Key | Purpose | Default |
| --- | --- | --- |
| `metadata` | Project dependency metadata | Detected metadata path |
| `requirements` | Requirements or minimum constraints | Detected requirements path |
| `mode` | `minimum-constraints` or `exact` comparison | Detected mode |

Detection selects the first pair whose files both exist:

1. `pyproject.toml` and `requirements/lowest.txt`: `minimum-constraints`.
2. `pyproject.toml` and `requirements.txt`: `exact`.
3. `infra/pyproject.toml` and `infra/requirements.txt`: `exact`.

If none exists, the first pair is the fallback; missing inputs fail validation rather than being
created. Individual settings override detected defaults.

In `minimum-constraints` mode, each runtime dependency must declare one `>=` lower bound and an
upper bound. Its corresponding constraint must be a single `name==version` pin equal to the lower
bound. A newer allowed version is still a mismatch for this fixture. In `exact` mode, normalized
dependency declarations must match the requirements. Neither mode installs dependencies.

Requirements inputs accept blank lines, full-line comments, and inline comments introduced by
whitespace followed by `#`. URL fragments without preceding whitespace remain part of the
requirement. Installer directives such as `-r` are still rejected; comment support does not make
Popo a complete installer requirements-file parser.

## Python-Policy Settings

`[tool.popo.python-policy]` supports the following non-empty strings:

| Key | Default |
| --- | --- |
| `metadata` | Dependency metadata path |
| `requires-python` | Dependency metadata's `project.requires-python`, or `>=3.13` |
| `python-version` | `3.13` |
| `python-version-file` | `.python-version` |
| `ruff-config` | Dependency metadata path |
| `ruff-target-version` | `py` plus `python-version` with periods removed |
| `mypy-python-version` | `python-version` |
| `workflow-directory` | `.github/workflows` |

The default `requires-python` comes from dependency metadata even when the Python-policy metadata
path is overridden. Set it explicitly when using a different policy. Popo checks the running
interpreter against that policy as well as checking repository declarations; run it with an
interpreter supported by both Popo and the consumer policy.

## Command Boundaries

Python-policy workflow inspection resolves literal versions, simple environment references, and
matrix references backed by inline lists or contiguous block lists. Block-list entries may be quoted
and have inline comments. This is static inspection, not evaluation of arbitrary workflow
expressions or full YAML semantics.

- `check-docs` reads repository-local Markdown; it does not require Python-policy configuration. It
  validates inline links and single-line reference definitions, including unused definitions, with
  heading and explicit HTML `<a id="...">` or `<a name="...">` anchors. It does not detect undefined
  reference labels, validate inline image links, or check external URLs. Fenced code examples are
  excluded from link scanning and heading-anchor discovery. Closing fences must use the same marker
  character and be at least as long as the opening fence. Plain directory links need no README;
  directory links with fragments resolve to that directory's `README.md`. Fragments are checked only
  on Markdown targets (`.md`, case-insensitive); other local files are checked for existence without
  parsing their format. Markdown anchors are cached within a check, not between checks.
- `check-github-actions-pins` defaults to `.github` under the selected root and accepts
  `--automation-directory`. Remote references must contain a non-empty action name and a full
  40-character hexadecimal commit SHA. Local (`./`) and container (`docker://`) references are
  exempt; the check does not verify repository existence or container-image immutability.
- `check-dependency-boundaries` and `check-python-policy` load the consumer configuration.
- `check-release-changelog` requires a release version and defaults to the root `CHANGELOG.md`; use
  `--changelog` to select another file.
- `check-all` combines documentation, action-pin, dependency, and Python-policy checks. It does not
  include release-changelog validation or accept the individual checks' path overrides.

Relative `--automation-directory` and `--changelog` values resolve against the working directory,
not `--root`. This differs from relative paths inside `[tool.popo]`.

## Validation Rules

Configuration sections must be TOML tables, supplied settings must be non-empty strings, and the
dependency mode must be supported. Unknown keys are currently ignored; check spelling against this
reference. Dependency and Python-policy commands load the complete configuration, so a malformed
section can fail either command.

Reported check or configuration failures return exit status `1`; successful checks return `0`.
Invalid command-line arguments are handled separately by the argument parser. Checks remain
read-only and do not repair files or change consumer policy automatically.

[configuration example]: ../README.md#configuration
