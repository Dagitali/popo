<!--
CONFIGURATION.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Consumer configuration fields, defaults, and command boundaries.

Maintainer Notes
- Verify defaults against src/popo/config/ and command flags against src/popo/cli.py.
- Keep consumer policy separate from Popo's supported runtime and development settings.
-->

# Configuration Reference

Commands that load consumer policy read standalone `popo.toml` when present, otherwise `[tool.popo]`
from `pyproject.toml` in the inspected root. Standalone settings use the file's top level: `[files]`
corresponds to `[tool.popo.files]`. The selected source is authoritative: settings are not merged,
and malformed standalone policy never falls back to Python metadata. Python package metadata remains
in `pyproject.toml`; standalone policy does not replace the inputs of Python-specific validators.

`source-inventory` uses CLI arguments and committed Git objects without loading consumer policy.

Select the root with `--root`; otherwise it uses the working directory. Relative configured paths
are resolved against that root. See the [configuration example] for a Python starting point and the
[guardrail guide] for a language-neutral consumer.

- [Check Selection](#check-selection)
- [Guardrail Parity](#guardrail-parity)
- [Output and Explanation](#output-and-explanation)
- [Dependency Settings](#dependency-settings)
- [Python-Policy Settings](#python-policy-settings)
- [Swift-Policy Settings](#swift-policy-settings)
- [Automation Settings](#automation-settings)
- [File Policy Settings](#file-policy-settings)
- [Repository Safety Settings](#repository-safety-settings)
- [Hosted Audit Settings](#hosted-audit-settings)
- [Command Boundaries](#command-boundaries)
- [Validation Rules](#validation-rules)

## Check Selection

Top-level `checks` (or `tool.popo.checks`) replaces `check-all`'s default selection with an ordered,
nonempty array of unique full command names. Profiles under `[profiles.NAME]` (or
`[tool.popo.profiles.NAME]`) require exactly one `checks` field with the same validation. `popo
check-all --profile NAME` selects that profile instead of top-level checks. No profile is selected
automatically. Missing profiles, duplicate names, empty arrays and unknown checks fail.

Selectable commands are `check-docs`, `check-github-actions-pins`, `check-dependency-boundaries`,
`check-python-policy`, `check-automation-contracts`, `check-repository-safety`,
`check-required-files`, `check-file-headers`, `check-guardrail-parity`, `check-python-source`,
`check-swift-source`, `check-swift-policy`, `check-logs`, `check-test-results`,
`check-swift-boundaries` and `check-python-boundaries`. Result/boundary commands were added in
v0.12.0. See [Swift toolchain policy], [source and log checks](source-and-log-checks.md), and
[result and boundary checks](result-and-boundary-checks.md) for their opt-in tables and limits.
Checks run in declared order. Reported failures and per-domain configuration failures do not hide
later selected checks. Unhandled filesystem and decoding errors retain their command-specific
propagation boundaries.

Without explicit selection, legacy baseline checks remain enabled and configured optional domains
join them. Explicit selection can omit configured domains; their settings are generally not loaded.
Dependency and Python-policy settings share a loader, so either selected check validates both
domains' configuration. A selected file/header/safety check still requires its own configuration.
Automation retains its standalone workflow defaults. External actionlint, hosted auditing and
version-dependent release validation remain explicit commands, outside aggregate selection.

## Guardrail Parity

`[guardrails]` (or `[tool.popo.guardrails]`) declares one literal invocation chain. See the
[guardrail guide] for a working example and static-inspection limits.

| Key | Default | Purpose |
| --- | --- | --- |
| `makefile` | `Makefile` | Make recipe source |
| `hooks` | `.pre-commit-config.yaml` | Pre-commit configuration |
| `workflow` | `.github/workflows/ci.yml` | Workflow source |
| `target` | `guardrails` | Literal Make target |
| `hook` | `popo` | Unique local hook ID |
| `job` | `guardrails` | Workflow job key |
| `step` | `popo` | Unique step ID within that job |
| `profile` | `guardrails` | Explicit named profile invoked by Make |

Paths must stay within the repository, including symlink resolution; absolute and parent paths are
rejected. Identifiers contain ASCII letters, digits, underscores or hyphens, with a letter, digit or
underscore first. Unknown settings fail. The delegated profile must exist and can include
`check-guardrail-parity` itself: the checker inspects literal commands without invoking them.

## Output and Explanation

Native offline commands accept `--format text|json`; text remains the default. JSON schema version
one contains `command`, aggregate `passed`, and ordered `checks`. Each result contains `check` (the
stable public command identifier), `passed`, `diagnostics` and a success-only `summary`. Diagnostics
contain `severity: "error"` and the original `message`. Selection failures use the `configuration`
identifier. No guessed file locations or finer rule IDs are added to existing messages. JSON output
contains no text PASS/FAIL prefixes. Exit status remains zero or one.

`popo explain [--profile NAME] [--format json]` reports the resolved root, selected configuration
path and its existence, selection reason and ordered check names. It does not run validators or
verify their domain settings, referenced inputs, installed tools, or hosted enforcement. Invalid
selection is still a failure. Hosted auditing retains its separate JSON schema; external actionlint
retains its original streams and status. Argument-parser errors retain argparse's stderr/status two.

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
dependency declarations must match the requirements. Package names are case-insensitive, and runs of
dots, underscores and hyphens are equivalent; this normalization does not discard extras, markers,
version specifiers or URL fragments. Neither mode installs dependencies.

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
| `workflow-parser` | `text`; optional `scoped` YAML observations |

The default `requires-python` comes from dependency metadata even when the Python-policy metadata
path is overridden. Set it explicitly when using a different policy. Popo checks the running
interpreter against that policy as well as checking repository declarations; run it with an
interpreter supported by both Popo and the consumer policy. Within the validator, shared
package/Ruff TOML is read once, with a single diagnostic for a missing or malformed shared input.
Configuration loading remains separate.

Every discovered workflow `python-version` declaration is checked. Unresolved supported env/matrix
references produce an unsupported-version diagnostic even when another declaration is valid.
Resolution remains text-based and does not model job-local scope or arbitrary expressions.

## Swift-Policy Settings

`[swift-policy]` (or `[tool.popo.swift-policy]`) declares supported stable compiler versions, a
preferred local selection, the expected package tools minimum and explicit workflow globs.
`check-swift-policy` has its own loader and requires no Python project metadata. It never invokes
Swift or executes manifests. See the [Swift toolchain policy] for the schema, scoped CI resolution,
explicit `--compiler-version` observations, version semantics and limits.

## Automation Settings

`[tool.popo.automation]` configures workflow, action, template, and generic YAML discovery, local
repository aliases, and template placeholder references. See the [automation contracts guide] for
all six settings, their defaults, an example, and the checker limitations.

These settings are arrays of nonempty strings; unknown keys are rejected. Discovery patterns are
relative to the inspected root, cannot be absolute or contain `..` path components, and must match
files. Empty arrays disable discovery categories. Resolved paths must remain within the repository.

The standalone `check-automation-contracts` command uses default workflow discovery when the table
is absent. Legacy `check-all` defaults include automation contracts when the table is present, even
if empty; explicit selections can include or omit that check. Automation loading is independent of
dependency and Python-policy settings.

## File Policy Settings

`[tool.popo.files]` supplies exact required paths for `check-required-files`. `[tool.popo.headers]`
supplies identity, ordered comment rules and explicit preservation exceptions for
`check-file-headers`. Neither command requires Python package metadata. Both tables are opt-in for
`check-all`; an explicit command fails if its own table is absent. See [file policies] for the
complete schema, matching rules and source-discovery boundaries.

## Repository Safety Settings

`[safety]` (or `[tool.popo.safety]`) configures workflow discovery patterns, reviewed
privileged-trigger exceptions, and npm manifest/lockfile pairs. The explicit command requires this
table; default aggregate selection includes it when configured. See [repository safety] for the
schema, UTC expiry rules, and the limits of static workflow and dependency inspection. These checks
do not execute workflow scripts or install npm packages.

## Hosted Audit Settings

`[hosted]` (or `[tool.popo.hosted]`) declares explicit repository expectations and approved
exception attestations.
Only `audit-github-settings` loads it; `check-all` stays offline. See [Hosted Settings Audit] for
the complete schema, statuses, permissions, and evidence limits. Unknown hosted keys and malformed
or duplicate scopes fail loading rather than being silently ignored.

Result and architecture policies are documented in [result and boundary
checks](result-and-boundary-checks.md). Result/boundary commands were added in v0.12.0; selection
requires their explicit tables.

## Command Boundaries

`source-inventory` is a standalone evidence generator requiring an explicit revision; it is not
selectable in profiles and does not use native check-result JSON. See [source inventories].

Python-policy workflow inspection resolves literal versions, simple environment references, and
matrix references backed by inline lists or contiguous block lists. Block-list entries may be quoted
and have inline comments. This is static inspection, not evaluation of arbitrary workflow
expressions or full YAML semantics.

- `check-docs` reads repository-local Markdown; it does not require Python-policy configuration. It
  validates inline links/images and single-line reference definitions, including unused definitions,
  with generated heading IDs and optional explicit HTML anchors. Full and collapsed reference labels
  use case folding and collapsed whitespace; undefined labels and conflicting destinations fail.
  Shortcut references and nested/escaped link syntax are not fully parsed. External URLs are not
  checked. Fenced/inline code and HTML comments are excluded from link scanning; fenced code and
  comments are excluded from heading-anchor discovery. Closing fences must use the same marker
  character and be at least as long as the opening fence. Plain directory links need no README;
  directory links with fragments resolve to that directory's `README.md`. Fragments are checked only
  on Markdown targets (`.md`, case-insensitive); other local files are checked for existence without
  parsing their format. Markdown anchors are cached within a check, not between checks. Local
  destinations must resolve within `--root`, including through symlinks and directory README
  targets. Parent-directory links within the root remain valid; escaping links fail even if the
  outside target exists. External URLs remain outside this local check. Source discovery excludes
  exact path components `.git`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.venv`,
  `__pycache__`, `build`, `dist`, `htmlcov`, and `node_modules`. Similar names such as
  `docs/building.md` remain checked, as does `.github`. These exclusions affect discovery only;
  explicit links into excluded directories still have their targets checked.
- `check-github-actions-pins` defaults to `.github` under the selected root and accepts
  `--automation-directory`. Remote references must contain a non-empty action name and a full
  40-character hexadecimal commit SHA. Local (`./`), valid self (`$/`), and container (`docker://`) references are
  exempt; the check does not verify repository existence or container-image immutability.
- `check-automation-contracts` loads automation settings and validates parsed YAML, local input
  contracts, composite steps, template metadata, and reference pins. `--pins-only` skips input,
  composite, and metadata checks; YAML parsing and local target resolution still run. See the
  [automation contracts guide] for exemptions and limits.
- `check-actionlint` selects configured workflows/templates or explicit in-root paths and runs an
  already-installed linter using a disposable self-reference compatibility view. `--actionlint`
  selects the executable/options. Validation and normalization share one read per automation file,
  including repeated or cyclic references. Source files are not rewritten, diagnostics retain source
  locations, and the exact external status is returned. Tool launch and source errors return one.
  Unlike native contract checks, this explicitly invokes an external tool; it is not included in
  `check-all` and does not install tools, execute workflow commands, or access the network itself.
- `check-dependency-boundaries` and `check-python-policy` load dependency and Python-policy
  configuration together; they do not load automation settings.
- `check-python-source`, `check-swift-source` and `check-logs` inspect configured inputs
  without executing source or native tools. `check-logs --log-root` selects an explicit artifact
  boundary; a relative override resolves against the working directory, not `--root`. They require
  their own opt-in policy tables; see [source and log checks](source-and-log-checks.md).
- `check-release-changelog` requires a release version and defaults to the root `CHANGELOG.md`; use
  `--changelog` to select another file.
- `check-all` uses explicit checks or a named profile when supplied, otherwise legacy baseline and
  configured opt-in checks. It does not include release-changelog validation or accept individual
  checks' path overrides or `--pins-only`; see [Check Selection](#check-selection).

Relative `--automation-directory` and `--changelog` values resolve against the working directory,
not `--root`. This differs from relative paths inside `[tool.popo]`.

## Validation Rules

Configuration sections must be TOML tables. Dependency and Python-policy settings must be non-empty
strings, and the dependency mode must be supported. Unknown keys in those sections are ignored;
check spelling against this reference. Both commands load those two sections, so a malformed
dependency or Python-policy section can fail either command. Automation settings instead require
arrays of nonempty strings and reject unknown keys; see [Automation Settings](#automation-settings).

Reported check or configuration failures return exit status `1`; successful checks return `0`.
Invalid command-line arguments are handled separately by the argument parser. Checks remain
read-only and do not repair files or change consumer policy automatically.

[automation contracts guide]: ../README.md#automation-contracts
[configuration example]: ../README.md#configuration
[file policies]: file-policies.md
[guardrail guide]: guardrails.md
[Hosted Settings Audit]: hosted-audit.md
[repository safety]: repository-safety.md
[source inventories]: source-inventory.md
[Swift toolchain policy]: swift-policy.md
