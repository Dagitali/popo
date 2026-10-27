<!--
swift-policy.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Explicit Swift compiler selections, package minimums and scoped CI declarations.

Maintainer Notes
- Keep compiler versions, tools versions and language modes distinct.
- Never infer runtime verification from declaration-only checks.
-->

# Swift Toolchain Policy

`check-swift-policy` is an opt-in declaration check in the v0.11.0 release scope. It reads local
policy, a version file, the package tools-version header and selected workflow inputs. It never
executes `Package.swift`, invokes Swift, installs a toolchain or changes consumer files. Python
project metadata is not required.

- [Configuration](#configuration)
- [Version Semantics](#version-semantics)
- [Workflow Observations](#workflow-observations)
- [Invocation and Profiles](#invocation-and-profiles)
- [Python Policy Parity](#python-policy-parity)
- [Limits and Validation](#limits-and-validation)

## Configuration

Standalone `popo.toml` uses `[swift-policy]`; Python metadata uses `[tool.popo.swift-policy]`.

```toml
[swift-policy]
compiler-versions = ["6.1.2", "6.2.0"]
preferred-version = "6.1.2"
tools-version = "5.9"
manifest = "Package.swift"
version-file = ".swift-version"
workflow-globs = [".github/workflows/ci.yml"]
workflow-version-key = "swift-version"
require-preferred-in-ci = true
```

The compiler list, preference, tools version and nonempty workflow globs are required. The manifest,
version-file, input-key and CI-preference fields have the defaults shown. Unknown settings fail.
Paths and globs must be relative and cannot contain `..`; resolved manifest, version-file and
workflow inputs must stay inside the consumer root. Every workflow pattern must match files.

## Version Semantics

Supported versions are stable numeric `major.minor` or `major.minor.patch` strings. Missing patch
means zero: `6.1` equals `6.1.0`, not every `6.1.x` compiler. Leading zeroes, snapshots, suffixes,
Python version specifiers and arbitrary compiler-output strings are unsupported. Duplicate
normalized compiler versions fail configuration.

The preference must be in the compiler list, and every supported compiler must meet the expected
package tools minimum. The version file must match the preference; the manifest must start with a
literal `// swift-tools-version:` header matching the configured tools version. The rest of the
manifest is not interpreted. A newer preferred compiler and an older package minimum are valid.

Compiler version, package tools version and Swift language mode are separate facts. The tools header
also selects manifest API compatibility; it is not an exact compiler pin. Language modes, Xcode
build settings, deployment targets and dependency resolution are outside this check. See the
[package tools-version documentation].

## Workflow Observations

Every selected workflow must declare the configured input in `jobs.JOB.with` or
`jobs.JOB.steps[N].with`. This identifies the consumer's explicit contract, not the identity of an
action or proof that a setup command executed. Use quoted version strings to prevent YAML numeric
coercion.

Supported values are literals, `${{ env.NAME }}` and `${{ matrix.NAME }}`. Environment precedence is
workflow, job, then step. Matrix values come only from that job's nonempty literal list. Job-scoped
values are never borrowed from another job. General expressions, nested references, dynamic matrices
and matrix `include`/`exclude` resolution are unsupported and produce findings.

Every resolved CI version must be supported. At least one must match the preference across the
selected workflows unless `require-preferred-in-ci=false`. Missing, malformed, escaping or
unreadable inputs fail; unsupported resolution never silently selects a guessed version. Findings
identify files and input selectors without echoing invalid version text or filesystem exceptions.

## Invocation and Profiles

```console
popo check-swift-policy
popo check-swift-policy --compiler-version 6.1.2 --format json
```

`--compiler-version` accepts an explicit caller-supplied observation. It must be supported but need
not equal the preferred compiler, permitting compatibility-matrix runs. Omission checks declarations
only; it does not establish the installed compiler version or authenticate supplied observations.
The option belongs to the individual command, not `check-all`.

```toml
[profiles.swift]
checks = ["check-swift-policy", "check-swift-source"]
```

Configure both domains before using that example profile. Use the same profile from Make, pre-commit
and CI; [shared guardrails] can inspect the entry-point contract separately. Explicit checks and
profiles select this command; implicit selection adds it when the Swift policy table is present.
Legacy baseline checks remain unchanged, so Swift-only consumers should select an explicit profile
rather than inheriting Python-specific baseline checks.

## Python Policy Parity

Python and Swift have separate policy loaders and language-specific version semantics. Python
retains its dependency-derived metadata defaults and PEP 440 comparisons. Its existing text-based
workflow behavior remains the default. To use the shared scoped YAML observer, set
`workflow-parser="scoped"` in `[python-policy]` or `[tool.popo.python-policy]`.

Scoped Python mode reads `python-version` inputs in the same job/step locations and reports missing
inputs, unsupported expressions and read/parse errors as diagnostics. Legacy text mode keeps its
published resolution and I/O propagation behavior. Declaration and source-convention checks remain
separate commands for both languages.

## Limits and Validation

These checks inspect declarations, not workflow execution, trigger coverage, action identity or
successful builds. Each language's compiler, formatter, documentation and integration checks retain
their own responsibilities. Tools and compiler versions do not imply a Swift language mode.

The deterministic suite uses synthetic manifests and workflows, scoped-reference cases, malformed
inputs and read-only snapshots. Installed-command tests exercise wheels and sdists without requiring
Swift. Those results do not establish hosted cross-platform or native Swift compiler success.

[shared guardrails]: guardrails.md
[package tools-version documentation]: https://docs.swift.org/package-manager/PackageDescription/PackageDescription.html
