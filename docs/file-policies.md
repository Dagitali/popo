<!--
file-policies.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Consumer-owned required-file and header policy reference.

Maintainer Notes
- Keep these checks read-only and independent of consumer languages or brands.
- Document literal matching and preservation boundaries rather than claiming a full formatter.
-->

# File Policies

- [Required Files](#required-files)
- [Header Configuration](#header-configuration)
- [Rules and Templates](#rules-and-templates)
- [Directives and Comment Formats](#directives-and-comment-formats)
- [Discovery and Preservation](#discovery-and-preservation)
- [Commands and Adoption](#commands-and-adoption)

## Required Files

```toml
[tool.popo.files]
required = ["README.md", "SECURITY.md", ".github/workflows/ci.yml"]
```

Paths are exact root-relative POSIX filenames, not globs or directory requirements. The nonempty
array rejects duplicates, absolute paths, parent traversal, backslashes and drive-like paths.
`check-required-files` reports every missing/non-file entry and rejects resolved symlinks outside
the repository. Path-resolution and inspection errors are reported alongside subsequent missing
paths rather than stopping the check. It does not prescribe filenames or infer that an existing
document is correct.

## Header Configuration

```toml
[tool.popo.headers]
project = "Example"
notice = "Copyright Example"

[[tool.popo.headers.rules]]
patterns = ["*.py"]
format = "python"
prefix = ":mod:`{module}` module.\n\n{project}.\n\n{notice}\n\n"

[[tool.popo.headers.rules]]
patterns = ["*.sh"]
format = "hash"
first-line-prefix = "#!"
prefix = "{filename}\n{project}\n\n{notice}\n\n"
required-text = ["\n\nMaintainer Notes\n- "]

[[tool.popo.headers.exceptions]]
patterns = ["*.json", "*.png"]
reason = "Strict data consumers and binary artwork do not support comment headers."
```

Unknown keys and unsupported formats fail loading. Identity and notice are consumer values, not
license grants. Rule templates determine where those values must appear; configuring a notice alone
does not automatically insert or enforce it. Files are never changed.

## Rules and Templates

Patterns use case-sensitive `fnmatch` against the full root-relative POSIX path; `*` can span
separators. Exceptions are evaluated before rules, after containment checks. The first matching rule
wins, so put specific filenames and directive-sensitive rules before general extensions.
Unclassified maintained files fail until a rule or explicit reasoned exception covers them.

Each rule requires nonempty `patterns`, `format` and `prefix`. Prefix templates allow only
`{filename}`, `{module}`, `{project}` and `{notice}`; literal braces use `{{` and `}}`. Filename is
the basename; module is the filename stem with hyphens replaced by underscores, not a guessed
package path. Attribute/index lookup, conversion and format specifications are rejected.

`purpose-required` defaults to true and requires a nonempty first paragraph after the prefix.
`required-text` is an optional array of literal substrings required in that remainder. These checks
validate configured structure, not the accuracy or completeness of prose.

## Directives and Comment Formats

| Format | Leading Content Inspected |
| --- | --- |
| `raw` | Literal source prefix; useful for language-specific banners |
| `python` | Leading module docstring from Python AST; malformed source fails |
| `hash` | Contiguous `#` comments, with an optional initial shebang |
| `slash` | Contiguous `//` comments |
| `html` | Leading `<!--` comment with its own opening line |
| `xml` | The same comment, after optional XML declaration/DOCTYPE lines |
| `block` | Leading `/*` comment with its own opening line |

`first-line` requires an exact first line and removes it before header extraction.
`first-line-prefix` instead requires a prefix such as a shebang or tools-version directive. They are
mutually exclusive. `trim-after-first-line = true` permits blank lines immediately after that
directive, for formats with a required visible title preceding the comment.

`preamble-prefixes` is an ordered array of optional first-line prefixes to skip once each. Hash
headers may have a standalone `#` separator after a skipped preamble. This can preserve a YAML
language-server directive. Rules do not parse arbitrary XML, run source code or rewrite directives.
Keep language-specific abstraction/DocC checks in their existing validators.

## Discovery and Preservation

Header discovery asks Git for tracked and unignored files, including hidden and untracked paths;
deleted paths are not read. Dangling symlinks remain in the inventory so containment checks run
before preservation exceptions. Git discovery has a 30-second timeout and failures remain failures.
When Git is unavailable or the root is not a working tree, discovery falls back to local recursive
files. `ignored-directories` names literal path components rather than substrings or globs. Defaults
exclude `.git`, `.venv`, `.build`, `.swiftpm`, `__pycache__`, `.pytest_cache`, `.mypy_cache`,
`.ruff_cache`, `build`, `dist` and `node_modules`. An explicit list replaces these defaults.

Preservation exceptions require patterns and a reason. Their contents are not decoded, so binary
assets and strict data files remain intact. Exceptions do not authorize symlink escapes. Unexpected
binary/read errors in non-exempt files fail. No credentials or configuration callbacks are loaded.

## Commands and Adoption

```console
popo check-required-files --root .
popo check-file-headers --root .
```

Zero means the configured boundary passed; missing policy, malformed configuration or violations
return one. Explicit commands load only their own policy. `check-all` adds both checks when their
tables are present, alongside its existing checks; it is not a generic task runner.

Before removing a consumer's local guards, translate all existing filenames, formats, directives and
exceptions, compare positive/negative fixtures, and verify a tested released immutable pin. A
source-checkout test does not make a capability available in an older installed release.
