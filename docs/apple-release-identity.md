<!--
apple-release-identity.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Read-only Apple release identity validation and selected-field reports.

Maintainer Notes
- Keep exact selectors, numeric normalization and output schema aligned.
-->

# Apple Release Identity

This **unreleased** command validates and reports one explicitly selected native release identity.
It is unavailable in v0.15.0. The command reads consumer policy and one Xcode project, never invokes
Git or Apple tools, and never writes files.

- [Usage](#usage)
- [Configuration](#configuration)
- [Validation and Normalization](#validation-and-normalization)
- [Reports and Failures](#reports-and-failures)
- [Adoption and Limits](#adoption-and-limits)

## Usage

```sh
popo apple-release-identity --root /path/to/repository
popo apple-release-identity --root /path/to/repository --tag v1.2.0 --format json
```

This is a standalone report command, separate from native check-result aggregation. It cannot be
selected in `checks` or profiles. Missing policy fails direct invocation; the command is never
implicitly enabled. A tag is checked only when explicitly passed; environment variables and current
Git branches/tags are ignored.

## Configuration

In `pyproject.toml`:

```toml
[tool.popo.apple-release]
project = "Example.xcodeproj/project.pbxproj"
target = "Example"
configurations = ["Debug", "Release"]
# Optional defaults:
product-type = "com.apple.product-type.application"
tag-prefix = "v"
```

Standalone `popo.toml` uses `[apple-release]`. Target, project and a nonempty unique configuration
list are mandatory. Names are exact and case-sensitive. The complete native configuration set must
match: additional, missing, unnamed, duplicate-name and repeated-reference configurations fail.
There must be exactly one matching native target of the required product type. Unrelated targets,
including unit/UI test bundles, do not contribute version/build values.

`project` is a literal confined POSIX filename, not a glob. Paths cannot be absolute or contain
parent traversal, empty/dot components, backslashes or control characters. Symlink resolution must
remain inside the selected root. `tag-prefix` permits an empty string or a literal prefix without
whitespace/control characters; no pattern or shell evaluation occurs. Unknown settings fail.

## Validation and Normalization

The command reads only explicit `MARKETING_VERSION` and `CURRENT_PROJECT_VERSION` settings from
every selected configuration. Missing values, non-string values and build-variable expressions fail.

- Versions require two or three dot-separated **ASCII numeric** components. Two components gain
  `.0`; three remain unchanged. Prerelease/build suffixes and surrounding whitespace fail.
- Builds require an ASCII digit string representing a positive integer. Zero, signs, decimal
  points and whitespace fail. Output converts the value to an integer.
- Every configuration must agree on the **literal spelling** of both fields before normalization.
  Mixed `1.2`/`1.2.0` or `7`/`007` declarations fail even when their converted values coincide.
- Agreed leading zeroes remain accepted: `01.02` becomes `01.02.0`, and `007` becomes integer `7`.
  This is numeric release normalization, not strict SemVer enforcement or complete validation of
  every platform's permitted bundle-version syntax.
- If supplied, the tag must exactly equal the configured prefix plus normalized version. Builds
  are not part of tag comparison, and the command does not verify that the tag exists in Git.

These rules preserve common existing numeric release formats. Compared with permissive readers,
ASCII digits and unique configuration references are intentional stricter requirements.

## Reports and Failures

Default text output is `Release identity: 1.2.0 / build 7`. JSON emits only:

```json
{"schema_version": 1, "version": "1.2.0", "build": 7}
```

The identity schema is independent of native check-result JSON. No project path, target name,
configuration list or unrelated setting enters the successful report. Version and build are
intentionally returned to the caller; they should be treated as release metadata.

Success returns zero. Configuration, input, structure, value and tag failures return one with empty
stdout and a generic stderr diagnostic. Values, paths, malformed source and native exception text
are not disclosed. Argument errors follow usage status two. Callers retain subprocess deadlines,
artifact writes and their own failure handling; never replace existing evidence after a failed call.

## Adoption and Limits

Pin a released immutable version before deleting consumer production readers. Call the public CLI,
parse successful JSON once, and use its normalized fields for candidate evidence. Move parser,
normalization and tag-format matrices into Popo; retain essential consumer selection/caller tests.

This shares Xcode reference resolution with [Apple metadata](apple-metadata.md). It reads an
explicit OpenStep subset; there is no inheritance, xcconfig resolution, build-variable expansion,
compilation, signing, archive inspection, evidence approval or publishing. Source identity does not
prove a built application contains those values or that a release is ready. Scheme/test-plan
relationships and working-tree fingerprints remain separate capabilities.
