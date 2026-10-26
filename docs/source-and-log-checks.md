<!--
source-and-log-checks.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Opt-in source conventions and redacted artifact validation.

Maintainer Notes
- Keep policy choices in consumer configuration and checks read-only.
-->

# Source and Log Checks

- [Status and Boundaries](#status-and-boundaries)
- [Python Conventions](#python-conventions)
- [Swift Documentation](#swift-documentation)
- [Redacted Logs](#redacted-logs)
- [Selection and Adoption](#selection-and-adoption)

## Status and Boundaries

These commands are unreleased additions. They inspect configured files without importing source,
executing tools, changing files, or installing dependencies. Existing checks and default selection
remain unchanged unless a consumer explicitly configures one of these domains.

Each domain requires a nonempty `include` list. Patterns are root-relative `Path.glob` patterns;
`exclude` uses case-sensitive `fnmatch` on root-relative POSIX filenames. Inputs are deduplicated
and sorted. Every include pattern must match at least one file after exclusions. Missing inputs,
invalid UTF-8, and symlinks escaping the selected root fail; exclusions are applied before reading.
Configured patterns must be relative and cannot contain `..`. Source-guide paths obey the same
repository boundary. Validators report relative locations and rule descriptions, not source lines.

These checks complement compilers, formatters, type checkers and DocC. They do not replace them.

## Python Conventions

```toml
[tool.popo.python-source]
include = ["src/**/*.py", "tests/**/*.py"]
exclude = ["src/generated/*"]
annotations = true
parameter-lines = true
alphabetical-methods = true
docstring-width = 79
max-module-lines = 1000
```

`check-python-source` parses ASTs without executing inspected modules. It can require annotations on
all parameters, including `self`, and returns; require one physical line per parameter and its
default; and require instance methods to appear in alphabetical order within each class. Instance
methods are identified by their first positional parameter being named `self`. Empty signatures and
signatures containing only `self` are exempt from the parameter-layout rule. Positional-only,
keyword-only, async and variadic signatures are included.

Annotation, parameter-layout and method-order options default to false. Docstring width defaults to
79 physical characters, including indentation and delimiters. Module length defaults to 1000
physical lines. Numeric limits must be positive integers; booleans are not integers here. Syntax
errors return location-only diagnostics. An annotation's presence does not establish type validity.
Use existing lint tools for overlapping rules instead of enabling duplicate enforcement
unnecessarily.

## Swift Documentation

```toml
[tool.popo.swift-documentation]
include = ["App/**/*.swift", "AppTests/**/*.swift"]
file-overviews = true
declaration-docs = true
declaration-spacing = true
source-guide = "Docs/App.docc/SourceFiles.md"
```

`check-swift-documentation` requires a leading `/// ` overview and adjacent `///` comments on
nominal declarations and extensions, with a blank line before the documentation. Attribute-only
lines between documentation and declarations are supported. All three switches default to true. An
optional source guide must contain each selected root-relative Swift filename in backticks. No guide
check runs when `source-guide` is empty, which is its default.

Lexical masking excludes line comments, nested block comments, ordinary strings, multiline strings
and raw strings before finding declarations. This is a lightweight guard, not SwiftSyntax or a
compiler: regex literals, semantic resolution and the full Swift grammar are unsupported. Block DocC
comments are not accepted as substitutes for the configured `///` convention. Keep compiler, DocC
and representative syntax tests in the consumer's validation.

## Redacted Logs

```toml
[tool.popo.logs]
include = ["**/console-*.txt"]

[tool.popo.logs.patterns]
invalid-frame = "Invalid frame dimension"
state-update = "Modifying state during view update"
```

`check-logs --log-root /explicit/exported-artifacts` reads artifacts beneath the explicitly selected
root. Without `--log-root`, it uses the consumer repository root. Policy is always loaded from
`--root`; the log-root override does not load policy from an artifact directory.

Patterns are nonempty, case-sensitive literal substrings, not regular expressions. Rule IDs must
contain only ASCII letters, digits, periods, underscores or hyphens. Findings contain only relative
filenames, line numbers and configured rule IDs. They never include matched lines or patterns.
Filenames and rule IDs remain visible: use nonsensitive artifact names and identifiers. This is not
a secret scrubber for original logs; retain and share artifacts according to consumer privacy
policy.

Empty, excluded, unreadable or undecodable evidence cannot pass as clean logs. Every matching rule
is reported, including multiple matches on a line. No default diagnostic patterns are imposed.

## Selection and Adoption

All commands accept `--root` and the existing `--format text|json` reporting options. They can be
selected by explicit checks or named profiles, and aggregate checks continue after reported domain
configuration or validation failures.

```toml
[tool.popo.profiles.source]
checks = ["check-python-source", "check-swift-documentation"]
```

```sh
popo check-all --profile source
popo check-logs --log-root /explicit/exported-artifacts --format json
```

When selection is implicit, configuring a domain opts its corresponding check into `check-all`.
Prefer a separate log command when artifacts only exist after tests. Consumers with explicit
profiles must add the new command names themselves. Before removing a local checker, upgrade an
immutable dependency pin to a released version containing the command, validate equivalent policy
and representative negative cases, and preserve integration tests for the installed public CLI.
