<!--
apple-metadata.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Opt-in Apple property-list and explicit Xcode settings contracts.

Maintainer Notes
- Keep supported selectors and limitations aligned with the public CLI.
-->

# Apple Metadata

This **unreleased** command checks consumer-owned expectations without Xcode, signing tools or
platform credentials. It is not available in v0.14.0. Checks read files and never modify them.

- [Usage](#usage)
- [Contracts](#contracts)
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

## Selection and Diagnostics

Paths are literal repository-relative POSIX filenames, not globs. Absolute paths, parent traversal,
empty components, backslashes and control characters are rejected. Symlink resolution must remain
inside the root. Successful decoded inputs are shared by rules during one invocation.

Each failed rule reports its configured ID and a generic input/policy failure; actual or expected
values, absolute paths and native parser exception text are not emitted. Independent rules continue
after a failure. Choose non-sensitive IDs. Success returns zero; input/policy failures return one;
argument errors follow the normal usage status of two.

## Limits and Adoption

The OpenStep reader supports explicit dictionaries, arrays, comments and JSON-compatible quoted
strings. It is not an Xcode build-settings evaluator. No variable expansion, inherited settings,
xcconfig resolution, SDK conditions or computed deployment values are evaluated. Unsupported syntax
fails rather than establishing a configuration's resolved build settings.

Source declarations do not establish actual signed capabilities or legal export-compliance status. A
consumer may explicitly select an already-built plist, but signatures, provisioning and archive
validation remain separate. Schemes and test-plan/source-method cross-references are not
implemented.

Keep application identities and platform decisions in consumer configuration. Compare the public
candidate CLI against existing checks using real metadata and representative mutations. Pin a
released immutable dependency before deleting production validators. Move shared parser/schema
matrices to Popo, and retain only essential consumer-policy and caller integration tests.
