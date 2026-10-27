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
- [Swift Source](#swift-source)
- [Redacted Logs](#redacted-logs)
- [Selection and Adoption](#selection-and-adoption)

## Status and Boundaries

These commands are part of the v0.11.0 release scope. They inspect configured files without
importing source, executing tools, changing files, or installing dependencies. Existing checks and
default selection remain unchanged unless a consumer explicitly configures one of these domains.

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
documentation-width = 79
max-file-lines = 1000
file-overviews = false
declaration-docs = false
parameter-docs = false
return-docs = false
raises-docs = false
source-guide = "Docs/PythonSources.md"
```

`check-python-source` parses ASTs without executing inspected modules. It can require annotations on
all parameters, including `self`, and returns; require one physical line per parameter and its
default; and require instance methods to appear in alphabetical order within each class. Instance
methods are identified by their first positional parameter being named `self`. Empty signatures and
signatures containing only `self` are exempt from the parameter-layout rule. Positional-only,
keyword-only, async and variadic signatures are included.

Annotation, parameter-layout and method-order options default to false. Documentation width defaults
to 79 physical characters, including indentation and delimiters. File length defaults to 1000
physical lines. Numeric limits must be positive integers; booleans are not integers here. Syntax
errors return location-only diagnostics. An annotation's presence does not establish type validity.
Use existing lint tools for overlapping rules instead of enabling duplicate enforcement
unnecessarily.

Python documentation presence and callable contracts are separate opt-in switches. `file-overviews`
requires a module docstring; `declaration-docs` requires docstrings on classes and functions,
including nested definitions. `parameter-docs` checks NumPy `Parameters` names against the
signature, excluding an initial `self` or `cls`; grouped names and variadic parameters are
supported. `return-docs` requires a nonempty `Returns` section for value-return annotations or
explicit non-None returns, and `Yields` for generators. Literal `None`, `NoReturn` and `Never`
annotations, including quoted forward references and typing-qualified NoReturn/Never, do not by
themselves require a return section. `raises-docs` requires a nonempty `Raises` section for explicit
raise statements, including locally caught ones. These are syntax-based coverage rules, not
exception escape analysis, type validation, prose-quality assessment or proof that every indirect
exception is documented. Nested callable bodies do not contribute return/yield/raise requirements to
their enclosing function.

For either language, a nonempty `source-guide` requires each selected root-relative filename in an
exact backtick span. The guide must remain inside the repository, including after symlink
resolution; missing, unreadable and invalid UTF-8 guides fail. Empty `source-guide` disables this
check. File length counts physical lines, and documentation width includes indentation and
delimiters. These shared mechanics do not require identical language conventions.

## Swift Source

```toml
[tool.popo.swift-source]
include = ["App/**/*.swift", "AppTests/**/*.swift"]
file-overviews = true
declaration-docs = true
declaration-spacing = true
member-docs = false
parameter-docs = false
return-docs = false
raises-docs = false
parameter-lines = false
documentation-width = 79
max-file-lines = 1000
source-guide = "Docs/App.docc/SourceFiles.md"
```

`check-swift-source` uses the configured Swift documentation rules: `file-overviews`,
`declaration-docs` and `declaration-spacing` default to true. A file overview is a leading `/// `
comment; nominal types and extensions require adjacent `///` documentation, with a blank line before
that documentation. Attribute-only lines between documentation and declarations are supported.

`member-docs` optionally requires documentation on recognized functions, initializers,
deinitializers, subscripts and properties outside callable/closure bodies. `parameter-docs` checks
internal argument names using DocC `- Parameter name:` entries or nested `- Parameters:` lists.
`return-docs` requires `- Returns:` for named functions and subscripts whose result is not spelled
`Void`, `()`, `Swift.Void`, `Never` or `Swift.Never`; type aliases are not resolved; `raises-docs`
requires `- Throws:` for `throws`/`rethrows` signatures. Each field must have content.
`parameter-lines` requires each explicit parameter and its default on its own physical line after
the declaration line. These switches default to false; Swift does not inherit Python's annotation or
alphabetical-method policies. Documentation width defaults to 79 physical characters and file length
to 1000 physical lines.

Lexical masking excludes line comments, nested block comments, ordinary strings, multiline strings
and raw strings before finding line-leading declarations. Balanced parentheses and type/default
separators support named callable signatures and multiline parameters. Recognized signatures that
cannot be inspected fail when callable checks are enabled. Declarations sharing a physical line,
operator functions, regex literals, macros, semantic resolution and the full Swift grammar are
outside this lexical subset; both conditional-compilation branches are inspected. Block DocC
comments do not substitute for the configured `///` convention. This is not SwiftSyntax or a
compiler; keep compiler, DocC and representative syntax tests in the consumer's validation.

The earlier development names `check-swift-documentation`, `swift-documentation` and `swift_documentation.py`
were replaced by `check-swift-source`, `swift-source` and `swift_source.py`. No compatibility alias
is provided for these pre-release names. Update explicit profiles and consumer policy together. Both
language validators use the same discovery, redacted diagnostics, source-guide and limit helpers;
configuration stays in `popo.config.source_checks` rather than empty per-language modules.

Both source domains use `documentation-width` and `max-file-lines`, with identical width/file-limit
rule descriptions. The earlier development `docstring-width` and `max-module-lines` keys are rejected
as unknown settings; update consumer policy before adopting this revision. No compatibility aliases
are provided for these pre-release names.

Each language has a declaration frontend and documentation interpreter. `_python_declarations.py`
collects AST facts; `_swift_declarations.py` collects bounded lexical facts.
`_python_documentation.py` interprets NumPy sections and `_swift_documentation.py` interprets DocC
fields. Both expose `_documentation`, `_parameters` and `_section` with matching roles and
documented contracts. Each `_declaration_findings` checks one declaration before file-level
aggregation; shared `overview_findings` reports the file-overview policy using collector-supplied
facts. Presence and spacing decisions stay in their language interpreters. `_documentation` yields
shared immutable `CallableDocumentation` evidence for parameter names and required result/exception
content. NumPy retains grouped and starred names, Returns/Yields/Raises sections and case-sensitive
headings. DocC retains singular/grouped entries, optional name backticks, Returns/Throws fields and
case-insensitive labels. Declaration/member requirements and Swift documentation spacing remain
language-specific policies. Both consume the same immutable declaration/source fact model and shared
contract checks. Source validators own discovery, reading and reporting, while shared configuration
remains in `popo.config.source_checks`. This alignment does not add Swift annotation/method-order
rules or replace Python's `Yields` convention.

Both collectors use `_declaration_syntax` to discover syntax and `_declarations` to yield final
`Declaration` records. In both modules, `_declaration` converts one discovered declaration,
including nominal declarations and callables; `_declarations` preserves discovery order while
iterating those conversions. `_parameters` extracts `_ParameterSyntax` values, and
`_parameter_lines` checks their physical layout. Python aliases native `ast.arg` nodes; Swift uses
immutable records with named `offset` and `text` fields, preserving lexical spans and nested
type/default delimiters. Python's `_DeclarationSyntax` aliases native AST nodes; Swift's record of
that name retains lexical positions and bounded callable facts. Both expose `_signature` and
immutable `_Signature` observations with named parameter/layout fields. Python reads the parser's
existing signatures and retains annotation facts before body analysis; Swift balances source text
and retains trailing signature text and offsets. Swift excludes callable bodies from member
discovery. Both `_requirements` helpers produce the same immutable `CallableRequirements`
return/exception model. Python combines annotation observations with explicit returns, yields and
raises outside nested scopes; Swift reads return types and throws/rethrows from bounded signatures.
Parameter requirements remain separate in the shared `DeclarationFacts` model. These differences
remain intentional, along with Python annotation/ method-order facts and Swift documentation
attachment and spacing facts.

Both collectors isolate file-overview detection in `_file_overview`. Python requires the module's
leading nonempty docstring; a class or callable docstring alone is insufficient. Swift accepts a
column-zero `/// ` comment before the first code line, including one attached to the first
declaration. Strings and comments after code do not establish a Swift file overview. These are
explicit language-specific conventions, rather than equivalent documentation syntaxes.

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

Patterns are nonblank, single-line, case-sensitive literal substrings, not regular expressions.
Literals containing line separators are rejected because matching inspects one log line at a time.
Rule IDs must
contain only ASCII letters, digits, periods, underscores or hyphens. Findings contain only relative
filenames, line numbers and configured rule IDs. They never include matched lines or patterns.
Filenames and rule IDs remain visible: use nonsensitive artifact names and identifiers. This is not
a secret scrubber for original logs; retain and share artifacts according to consumer privacy
policy.

Selections with no files, or unreadable or undecodable selected files, cannot pass as clean logs.
An unresolvable selected root also returns a redacted diagnostic.
A readable empty log contains no matching diagnostics and can pass. Every matching rule is reported,
including multiple rules matching one line, in configured rule order. Repeated occurrences of one
literal produce one finding for that rule on the line. Files are inspected in sorted path order.
No default diagnostic patterns are imposed.

## Selection and Adoption

All commands accept `--root` and the existing `--format text|json` reporting options. They can be
selected by explicit checks or named profiles, and aggregate checks continue after reported domain
configuration or validation failures.

```toml
[tool.popo.profiles.source]
checks = ["check-python-source", "check-swift-source"]
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
