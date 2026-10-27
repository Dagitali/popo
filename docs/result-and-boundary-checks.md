<!--
result-and-boundary-checks.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Named result adapters and consumer-owned Python/Swift architecture restrictions.

Maintainer Notes
- Keep checks read-only and distinguish lexical guards from compiler evidence.
-->

# Result and Boundary Checks

- [Status and Scope](#status-and-scope)
- [Native Test Results](#native-test-results)
- [Python Boundaries](#python-boundaries)
- [Swift Boundaries](#swift-boundaries)
- [Profiles and Adoption](#profiles-and-adoption)

## Status and Scope

These are unreleased, opt-in offline commands. They do not run tests, compile Swift, export result
bundles, invoke consumer tools or write files. All use the existing text/JSON check-result schema
and aggregate selection/continuation behavior. No default application identity or folder layout is
imposed. Configuration is loaded from standalone `popo.toml`, otherwise `[tool.popo]` in
`pyproject.toml`; standalone examples below omit that prefix.

## Native Test Results

```toml
[test-results]
adapter = "xcode-summary"
include = ["*-summary.json"]
exclude = []
minimum-tests = 1
minimum-passed = 1
maximum-failed = 0
maximum-skipped = 0
maximum-warnings = 0
```

The named adapter accepts exported `xcresulttool get test-results summary` JSON. It requires a
mapping with nonnegative integer `totalTestCount`, `passedTests`, `failedTests` and `skippedTests`;
booleans, strings, floats and absent counts are invalid. Total must equal passed plus failed plus
skipped regardless of acceptance thresholds. `runtimeWarnings` must be a list when present; absence
means no warnings. Warning payloads are counted, not printed or interpreted.

Thresholds have the defaults shown and must be nonnegative integers. They are independent consumer
choices: relaxing skip/warning/failure limits does not relax schema or count consistency. Each
selected report must pass independently. No report can hide a failed sibling through aggregation.
Additional JSON fields are ignored; there is no arbitrary query/evaluation language.

```sh
popo check-test-results --results-root /explicit/exported-artifacts
popo check-test-results --summary /explicit/one-summary.json --format json
```

Without an override, discovery starts at the consumer repository root. `--results-root` selects an
explicit artifact directory while retaining configured patterns. `--summary` selects exactly one
literal filename, overrides include/exclude selection, and ignores siblings. These options are
mutually exclusive. Relative overrides resolve against the working directory. Policy always comes
from `--root`, not from artifact directories. Explicit file selection still rejects symlinks
escaping its parent directory.

Missing matches, invalid JSON/UTF-8 and read failures produce failing diagnostics. Reports and raw
exception messages are never echoed. Diagnostics retain relative filenames and fixed schema or
threshold identifiers, so artifact names must be nonsensitive. Original artifacts remain unchanged
and may contain private data; this validator is not a log scrubber or release approval.

## Python Boundaries

```toml
[[python-boundaries.layers]]
name = "core"
include = ["src/project/core/**/*.py"]
allowed-imports = ["project.core", "collections", "typing"]
forbidden-layers = ["ui"]
forbidden-symbols = ["os.system"]

[[python-boundaries.layers]]
name = "ui"
include = ["src/project/ui/**/*.py"]
```

Run `popo check-python-boundaries --root .`, or select it in a named profile used by Make,
pre-commit and CI. Configuration has the same layer, exclusion and confinement rules as Swift
boundaries. No Python boundary check activates without configuration or explicit selection.

Python uses ASTs without executing imports. Repository-relative paths, with an optional leading
`src/`, define dotted modules; `__init__.py` represents its package. Relative imports resolve from
that package. Forbidden layers reject imports of selected modules or their descendants. Import
allowlists accept a named module and descendants, including `from` imports; an empty list rejects
all imports. Unlike Swift, Python accepts dotted identifiers. Explicit forbidden symbols match names
and dotted attributes, including import aliases. Comments and strings do not count.

Imports in functions and conditional branches are inspected. Invalid syntax and relative imports
above the known package fail explicitly. Alternate package roots, dynamic imports, re-export chains
and local alias shadowing are not resolved. This is static guardrail evidence, not runtime
dependency isolation. Retain native tests and packaging checks independently.

## Swift Boundaries

```toml
[swift-boundaries]
exclude = ["Generated/*"]

[[swift-boundaries.layers]]
name = "core"
include = ["Engine/**/*.swift"]
allowed-imports = ["Foundation"]
forbidden-layers = ["adapters", "screens"]
forbidden-symbols = ["UserDefaults"]

[[swift-boundaries.layers]]
name = "adapters"
include = ["Adapters/**/*.swift"]
forbidden-layers = ["screens"]

[[swift-boundaries.layers]]
name = "screens"
include = ["Screens/**/*.swift"]
```

`check-swift-boundaries` indexes declared struct, class, enum, actor, protocol and typealias names
in each layer. It rejects references to names owned by explicitly forbidden layers, excluding names
also declared in the referencing layer. Explicit forbidden symbols always apply. When
`allowed-imports` is absent, imports are unrestricted; an empty list prohibits every recognized
import. Import rules operate on module names, including attributed and selective imports.

Layer names must be unique literal identifiers. References must name other configured layers;
unknown and self references fail. Include patterns must be nonempty. Patterns cannot be absolute or
contain `..`; symlink escapes fail. Every layer pattern needs at least one file after exclusions.
Unreadable/undecodable files fail the check. Files selected by multiple layers are checked under
each layer's restrictions. All source discovery and declaration indexing happen before dependency
checks, so configuration order does not define dependency direction.

This checker shares Swift lexical masking with source-convention validation. Nested comments and
ordinary, multiline and raw strings are masked. Findings identify locations, layer IDs, import
modules and configured/declared symbols without printing source lines. It is a conservative token
guard, not semantic dependency isolation: name collisions, local shadows, string interpolation,
regex literals, macros, same-line declarations and conditional compilation are not resolved. Both
conditional branches are inspected. Keep compiler/module boundaries and native tests independently.

## Profiles and Adoption

```toml
[profiles.architecture]
checks = ["check-swift-boundaries"]

[profiles.results]
checks = ["check-test-results"]
```

Explicit profiles do not activate automatically. With implicit selection, each configured domain
adds its corresponding check; use a separate command for reports created only after test execution.
Consumers should retain released local checks until an immutable released dependency contains these
commands and positive/negative parity is verified. Generic implementation tests belong here;
consumer tests retain policy selection, configured thresholds and runner integration.
