<!--
coverage-summaries.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Read-only reporting of exported coverage metrics.

Maintainer Notes
- Keep adapter defaults, JSON schema and CLI examples aligned with tests.
-->

# Coverage Summaries

This command is **unreleased**. It reads an existing exported report and emits aggregate Markdown or
JSON to stdout. It does not invoke LLVM, Xcode, a compiler or test tools, read source files, write
artifacts, install dependencies, or establish that tests passed. It is separate from `check-all` and
cannot be selected through check profiles. No percentage gate is imposed.

- [Commands](#commands)
- [Selection](#selection)
- [Adapter Contracts](#adapter-contracts)
- [Output and Failures](#output-and-failures)
- [Consumer Migration](#consumer-migration)

## Commands

```sh
popo coverage-summary llvm.json --adapter llvm \
  --include '**/Example/Domain/**/*.swift' \
  --include '**/Example/Persistence/**/*.swift' \
  --exclude '**/DerivedSources/**' > core-coverage.md

popo coverage-summary xccov.json --adapter xccov \
  --include '**/Example/**/*.swift' --exclude '**/Example/Tests/**' \
  --exclude '**/DerivedSources/**' --format json
```

The positional report filename is literal, including glob characters. Relative report paths are
relative to the working directory. The command does not discover a repository or read its policy
files and has no `--root` option. Redirect stdout only when an artifact is wanted; shell redirection
can create an empty destination before a failing command runs. Callers needing atomic replacement
should write to a temporary artifact and rename it only after a successful exit.

## Selection

At least one nonempty `--include` is required; repeat it to union selections. Repeat `--exclude` to
remove sources after inclusion. Patterns match complete, case-sensitive POSIX exporter paths using
`PurePosixPath.full_match`, including its `**` handling of nested or zero directories. Selections
are lexical and do not resolve symlinks or open source files. File extensions, generated folders,
test targets and production layers are consumer decisions; nothing is implicitly excluded.

The command validates filenames but reads metric fields only for selected sources. Unselected source
metrics do not contribute. Input and output contain no application-specific path defaults.

## Adapter Contracts

| Contract | `llvm` | `xccov` |
| --- | --- | --- |
| Export container | `data[].files[]` | `targets[].files[]` |
| Source path | `filename` | `path` |
| Metrics | `summary.{lines,functions,regions}.{covered,count}` | `coveredLines`, `executableLines` |
| Repeated paths | Block/file records are additive | Highest covered-line count per exact path |
| Conflicting duplicate denominators | Additive records retain their own totals | Rejected as ambiguous |
| Zero executable totals | Allowed, rendered as 0.0% | Rejected as unavailable |

`--zero-total allow` or `--zero-total reject` overrides the adapter default. Rejection applies to
aggregate metric totals, not individual empty files within an executable measurement. Zero covered
units with a positive denominator are valid measured zero coverage. No selected files is always
unavailable and fails, including an empty target export. Xcode targets without file records are
ignored. Counts must be nonnegative integers, excluding booleans, and covered cannot exceed total.

LLVM duplicate records deliberately remain additive for compatibility with block-based consumers;
the `files` output still counts distinct selected paths. This is not cross-build coverage merging.
Xcode keeps its best covered count when executable totals agree, independently of target order.
Combining different source revisions or compiler configurations is outside this command's scope.

## Output and Failures

Markdown includes a metric table and one-decimal percentages. Consumers supply their own titles,
measurement limitations and explanatory text. JSON uses the independent coverage schema:

```json
{
  "schema_version": 1,
  "adapter": "xccov",
  "files": 1,
  "metrics": {
    "lines": {"covered": 3, "total": 4, "percent": 75.0}
  }
}
```

Successful summaries contain aggregate counts rather than source filenames or raw report contents.
There is no release-readiness, test-success or live-service claim in this schema. It differs from
native check-result, inventory and hosted-audit JSON.

Exit status is 0 for a complete measurement, 1 for input/schema/selection failures and 2 for usage
errors. Input failures leave stdout empty and emit redacted diagnostics to stderr. Read/decode
errors do not echo paths or native exception text. Original reports remain private artifacts and are
not sanitized or modified by this command. Reports are decoded in memory. Normalization retains one
metric tuple per distinct selected path rather than every duplicate block/target record; it still
validates every selected record before reporting conflicting Xcode duplicate totals.

## Consumer Migration

Keep native export commands, fallback/unavailable handling, evidence retention and native exit-code
precedence in the consumer. Compare normalized metrics and selection against existing reports before
switching. Preserve explicit generated/test exclusions and zero-denominator choices. Retain consumer
integration tests for wiring and policy; shared parser and normalization matrices belong to this
package. Adopt a released immutable version before removing production consumer scripts.
