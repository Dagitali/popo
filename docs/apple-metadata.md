<!--
apple-metadata.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Opt-in Apple property-list and explicit Xcode settings contracts.

Maintainer Notes
- Keep supported selectors and limitations aligned with the public CLI.
-->

# Apple Metadata

Added in v0.15.0, this command checks consumer-owned expectations without Xcode, signing tools or
platform credentials. Checks read files and never modify them.

- [Usage](#usage)
- [Contracts](#contracts)
- [Metadata Extensions](#metadata-extensions)
- [Selection and Diagnostics](#selection-and-diagnostics)
- [Limits and Adoption](#limits-and-adoption)

## Usage

```sh
popo check-apple-metadata --root /path/to/repository --format json
```

The command supports the normal text/JSON check reports and explicit `check-all` profiles. It is
opt-in; absent policy fails direct invocation and is not selected by legacy defaults.

## Contracts

Example in `pyproject.toml`:

```toml
[tool.popo]
checks = ["check-apple-metadata"]

[[tool.popo.apple-metadata.rules]]
id = "export-compliance"
kind = "plist"
path = "Config/Info.plist"
absent = ["ForbiddenCapability"]
[tool.popo.apple-metadata.rules.expected]
ITSAppUsesNonExemptEncryption = false

[[tool.popo.apple-metadata.rules]]
id = "app-settings"
kind = "xcode"
path = "Example.xcodeproj/project.pbxproj"
target = "Example"
configurations = ["Debug", "Release"]
consistent = ["MARKETING_VERSION", "CURRENT_PROJECT_VERSION"]
[tool.popo.apple-metadata.rules.expected]
PRODUCT_BUNDLE_IDENTIFIER = "com.example.app"

[[tool.popo.apple-metadata.rules]]
id = "deployment-settings"
kind = "xcode"
scope = "project"
path = "Example.xcodeproj/project.pbxproj"
configurations = ["Debug", "Release"]
[tool.popo.apple-metadata.rules.expected]
IPHONEOS_DEPLOYMENT_TARGET = "27.0"
```

In standalone `popo.toml`, omit the `tool.popo` prefix and root table. At least one rule and one
requirement per rule are mandatory. IDs must be unique lowercase identifiers with optional digits
and hyphens. Unknown settings, empty selectors, duplicate selections and contradictory expected/
absent keys fail configuration validation.

Plist rules accept XML and binary files, including entitlement and privacy manifests. `expected`
checks exact typed values for named top-level keys; nested arrays/dictionaries compare completely.
Extra top-level keys are allowed unless listed in `absent`. Boolean false differs from integer zero
and the string `false`. Finite numbers, strings, Booleans, arrays and dictionaries are supported;
dates and binary expected values are not supported by the TOML contract.

Xcode rules default to `scope = "target"` and resolve one exact `PBXNativeTarget`. Explicit `scope =
"project"` instead selects the `PBXProject` referenced by `rootObject` and forbids a `target` field.
Each scope resolves named `XCBuildConfiguration` objects through its own configuration list.
`expected` values must be literal strings; `absent` forbids explicit settings. `consistent` requires
nonblank string values agreeing across the selected configurations. It does not validate semantic
version syntax or build-number format. Multiple rules can describe differing configuration variants;
additional unselected configurations are allowed.

## Metadata Extensions

The following additions are available in v0.17.0. Pin an immutable released dependency and validate
consumer adoption before replacing existing production checks.

```toml
[[tool.popo.apple-metadata.rules]]
id = "deployment-overrides"
kind = "xcode"
scope = "all-configurations"
path = "Example.xcodeproj/project.pbxproj"
required-anywhere = ["IPHONEOS_DEPLOYMENT_TARGET", "MACOSX_DEPLOYMENT_TARGET"]
optional-expected = {IPHONEOS_DEPLOYMENT_TARGET = "27.0", MACOSX_DEPLOYMENT_TARGET = "27.0"}

[[tool.popo.apple-metadata.rules]]
id = "local-capabilities"
kind = "plist"
path = "Config/Local.entitlements"
absent-patterns = ["(?i)icloud", "aps-environment"]

[[tool.popo.apple-metadata.coverage]]
id = "local-template-scope"
include = ["Config/Local*.entitlements"]
rule-ids = ["local-capabilities"]
```

`optional-expected` uses the same recursive, type-sensitive comparison as `expected`, but missing
keys are allowed. It does not establish that a key exists anywhere. `required-anywhere` separately
requires each listed key in at least one selected mapping; presence alone does not imply a type or
nonblank value. Combine the fields to enforce a baseline on every explicit declaration while
allowing individual configurations to omit an override. Xcode expectations remain literal strings.
Overlapping required/optional expectations, forbidden positive keys and invalid expressions fail
configuration loading.

`scope = "all-configurations"` inspects every declared `XCBuildConfiguration` object, including
project, test and unreferenced configurations. It requires at least one configuration and valid
build-setting dictionaries. It forbids both `target` and `configurations`, even empty declarations.
This does not traverse target relationships, evaluate inheritance or prove the project can build.
The existing target and project scopes retain their named-selection behavior.

`absent-patterns` contains Python regular expressions searched against explicit top-level key names.
Matching is case-sensitive unless the expression requests otherwise, such as `(?i)`. Patterns do not
inspect values or recursively inspect nested dictionaries. Existing literal `absent` checks remain
available. Findings never include matched keys, values, patterns or parser exception text.

Each `coverage` entry requires a unique non-sensitive `id`, nonempty `include` and nonempty
`rule-ids` referencing existing plist rules. Discovery uses case-sensitive filename globs within
literal directories: `Config/Local*.entitlements` is supported; wildcard directories and `**`
recursion are rejected. Discovery includes hidden, ignored and untracked matches and does not invoke
Git. Every selected directory must be readable; the union must contain at least one match. Matching
directories, broken links, escaping symlinks and uncovered filenames fail. Confined file symlinks
may pass when their lexical path has explicit rule coverage. Multiple patterns are unioned, so
repeated matches do not create duplicate findings.

Coverage compares literal paths with the selected plist rules; it does not infer that any rule has a
particular semantic strength. Consumers own the referenced rule IDs and expectations. For example,
adding another local template requires its own plist rule and its ID in the coverage list. Each
metadata rule still validates independently: path coverage does not excuse a malformed plist or a
policy violation. Discovery failures report the coverage ID after all metadata rule findings, using
the normal text/JSON schema. Inputs remain read-only; no atomic snapshot or race-free filesystem
validation is claimed.

## Selection and Diagnostics

Paths are literal repository-relative POSIX filenames, not globs. Absolute paths, parent traversal,
empty components, backslashes and control characters are rejected. Symlink resolution must remain
inside the root. Successful decoded inputs are shared by rules during one invocation.

Each failed rule reports its configured ID and a generic input/policy failure; actual or expected
values, absolute paths and native parser exception text are not emitted. Independent rules continue
after a failure. Choose non-sensitive IDs. Success returns zero; input/policy failures return one;
argument errors follow the normal usage status of two.

## Limits and Adoption

Shared inputs, including failed reads or parses, are read once per path/adapter in a validation run.
Each rule retains its own diagnostic; a later run inspects repaired or changed inputs afresh.

The OpenStep reader supports explicit dictionaries, arrays, comments and JSON-compatible quoted
strings. Structural delimiters used as scalar values or dictionary keys must be quoted. It is not an
Xcode build-settings evaluator. No variable expansion, inherited settings, xcconfig resolution, SDK
conditions or computed deployment values are evaluated. Unsupported syntax fails rather than
establishing a configuration's resolved build settings.

Source declarations do not establish actual signed capabilities or legal export-compliance status. A
consumer may explicitly select an already-built plist, but signatures, provisioning and archive
validation remain separate. Schemes and test-plan/source-method cross-references are not
implemented.

Keep application identities and platform decisions in consumer configuration. Compare the public
candidate CLI against existing checks using real metadata and representative mutations. Pin a
released immutable dependency before deleting production validators. Move shared parser/schema
matrices to Popo, and retain only essential consumer-policy and caller integration tests.
