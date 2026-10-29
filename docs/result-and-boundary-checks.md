<!--
result-and-boundary-checks.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Named result adapters and consumer-owned Python/Swift architecture restrictions.

Maintainer Notes
- Keep checks read-only and distinguish syntax guards from compiler evidence.
-->

# Result and Boundary Checks

- [Status and Scope](#status-and-scope)
- [Native Test Results](#native-test-results)
- [Python Boundaries](#python-boundaries)
- [Swift Boundaries](#swift-boundaries)
- [Profiles and Adoption](#profiles-and-adoption)

## Status and Scope

These opt-in offline commands were added in v0.12.0. They do not run tests, compile Swift, export
result bundles, invoke consumer tools or write files. All use the existing text/JSON check-result
schema and aggregate selection/continuation behavior. No default application identity or folder
layout is imposed. Configuration is loaded from standalone `popo.toml`, otherwise `[tool.popo]` in
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

The v0.13.0 backend shares Tree-sitter syntax with source-convention validation. Native import and
nominal/typealias nodes recognize same-line declarations and attributed/selective imports;
extensions do not establish new type ownership. Nested comments, ordinary/multiline/raw strings and
regex literals are masked before symbol matching. Findings retain locations, layer IDs, module names
and configured/declared symbols without printing source lines.

This remains a conservative token guard, not semantic dependency isolation: collisions, local
shadows, interpolation, macros and conditional-compilation semantics are not resolved. Both
conditional branches are inspected. Grammar recovery may produce partial syntax; successful parsing
is not compiler evidence. Keep compiler/module boundaries and native tests independently. Runtime
packages ship Python-accessible native parsers; no Swift installation or runtime grammar downloads
are required.

Both boundary adapters use shared `import_findings` evaluation with explicit native matching
policies. Python permits dotted descendants and reports unresolved relative or forbidden-layer
imports before allowlist violations. Swift matches module allowlists exactly and applies
forbidden-layer types through symbol rules. Import order and duplicate observations are retained.

Ownership is indexed once per selected path within a validation run, including paths whose source
cannot be read or parsed. Overlapping layers reuse these observations while evaluating their own
rules independently; later invocations build fresh indexes.

Both boundary adapters expose `_targets` ownership collectors. Python derives module identity from
paths even when source cannot be read or parsed; Swift derives nominal/typealias names from
available native syntax, excluding extensions. The adapters retain these different ownership models
behind the shared `BoundaryAnalyzer.targets` contract.

Both boundary adapters expose `_symbols` collectors returning shared `SymbolReference` observations.
Shared reporting filters exact case-sensitive restrictions, deduplicates line/name pairs and sorts
findings by line then name. Python retains dotted-name and import-alias expansion; Swift retains
masked-text token matching, including import tokens. These observations do not establish runtime
binding or semantic dependency resolution.

## Profiles and Adoption

```toml
[profiles.architecture]
checks = ["check-swift-boundaries"]

[profiles.results]
checks = ["check-test-results"]
```

Explicit profiles do not activate automatically. With implicit selection, each configured domain
adds its corresponding check; use a separate command for reports created only after test execution.
Consumers should adopt an immutable v0.12.0-or-later dependency containing these commands only after
positive/negative parity is verified. Generic implementation tests belong here; consumer tests
retain policy selection, configured thresholds and runner integration.
