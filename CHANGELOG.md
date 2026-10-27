<!--
CHANGELOG.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Public history of user-visible changes and compatibility corrections.

Maintainer Notes
- Preserve released entries and group pending changes under Unreleased.
- Keep local links and documented behavior consistent with repository sources.
-->

# Changelog

This file records concise, user-visible changes. The [release notes archive] indexes detailed scope,
compatibility, validation evidence, and release status; shared guidance lives in its [reading
guide].

The format is based on [Keep a Changelog], and this project follows [Semantic Versioning].

- [Unreleased](#unreleased)
- [\[0.12.0\] - 2026-10-27](#0120---2026-10-27)
  - [Added](#added)
  - [Changed](#changed)
  - [Fixed](#fixed)
- [\[0.11.0\] - 2026-10-26](#0110---2026-10-26)
  - [Added](#added-1)
  - [Changed](#changed-1)
  - [Fixed](#fixed-1)
- [0.10.0 - 2026-10-25](#0100---2026-10-25)
  - [Added](#added-2)
- [0.9.1 - 2026-10-24](#091---2026-10-24)
  - [Added](#added-3)
  - [Changed](#changed-2)
  - [Fixed](#fixed-2)
- [0.9.0 - 2026-10-24](#090---2026-10-24)
  - [Added](#added-4)
  - [Changed](#changed-3)
  - [Fixed](#fixed-3)
- [0.8.2 - 2026-10-23](#082---2026-10-23)
  - [Fixed](#fixed-4)
- [0.8.1 - 2026-10-23](#081---2026-10-23)
  - [Changed](#changed-4)
  - [Fixed](#fixed-5)
- [0.8.0 - 2026-10-23](#080---2026-10-23)
  - [Added](#added-5)
  - [Changed](#changed-5)
- [0.7.0 - 2026-10-22](#070---2026-10-22)
  - [Added](#added-6)
  - [Changed](#changed-6)
- [0.6.6 - 2026-10-08](#066---2026-10-08)
  - [Changed](#changed-7)
- [0.6.5 - 2026-10-08](#065---2026-10-08)
  - [Removed](#removed)
- [0.6.4 - 2026-10-07](#064---2026-10-07)
  - [Removed](#removed-1)
- [0.6.3 - 2026-10-07](#063---2026-10-07)
  - [Fixed](#fixed-6)
- [0.6.2 - 2026-10-07](#062---2026-10-07)
  - [Fixed](#fixed-7)
- [0.6.1 - 2026-10-07](#061---2026-10-07)
  - [Changed](#changed-8)
- [0.6.0 - 2026-10-07](#060---2026-10-07)
  - [Added](#added-7)
- [0.5.2 - 2026-10-06](#052---2026-10-06)
  - [Changed](#changed-9)
  - [Fixed](#fixed-8)
- [0.5.1 - 2026-10-06](#051---2026-10-06)
  - [Changed](#changed-10)
- [0.5.0 - 2026-10-06](#050---2026-10-06)
  - [Added](#added-8)
- [0.4.1 - 2026-10-04](#041---2026-10-04)
  - [Fixed](#fixed-9)
- [0.4.0 - 2026-10-04](#040---2026-10-04)
  - [Added](#added-9)
- [0.3.7 - 2026-10-01](#037---2026-10-01)
  - [Changed](#changed-11)
- [0.3.6 - 2026-10-01](#036---2026-10-01)
  - [Added](#added-10)
- [0.3.5 - 2026-10-01](#035---2026-10-01)
  - [Changed](#changed-12)
- [0.3.4 - 2026-10-01](#034---2026-10-01)
  - [Changed](#changed-13)
- [0.3.3 - 2026-09-30](#033---2026-09-30)
  - [Changed](#changed-14)
- [0.3.2 - 2026-09-30](#032---2026-09-30)
  - [Fixed](#fixed-10)
- [0.3.1 - 2026-09-30](#031---2026-09-30)
  - [Changed](#changed-15)
- [0.3.0 - 2026-09-30](#030---2026-09-30)
  - [Added](#added-11)
  - [Changed](#changed-16)
  - [Fixed](#fixed-11)
- [0.2.4 - 2026-09-27](#024---2026-09-27)
  - [Changed](#changed-17)
- [0.2.3 - 2026-09-27](#023---2026-09-27)
  - [Changed](#changed-18)
- [0.2.2 - 2026-09-26](#022---2026-09-26)
  - [Changed](#changed-19)
- [0.2.1 - 2026-09-26](#021---2026-09-26)
  - [Fixed](#fixed-12)
- [0.2.0 - 2026-09-26](#020---2026-09-26)
  - [Added](#added-12)
  - [Changed](#changed-20)
  - [Fixed](#fixed-13)
- [0.1.5 - 2026-09-24](#015---2026-09-24)
  - [Added](#added-13)
  - [Removed](#removed-2)
- [0.1.4 - 2026-09-24](#014---2026-09-24)
  - [Added](#added-14)
  - [Fixed](#fixed-14)
- [0.1.3 - 2026-09-24](#013---2026-09-24)
  - [Changed](#changed-21)
- [0.1.2 - 2026-09-24](#012---2026-09-24)
  - [Changed](#changed-22)
  - [Removed](#removed-3)
  - [Fixed](#fixed-15)
- [0.1.1 - 2026-09-24](#011---2026-09-24)
  - [Added](#added-15)
  - [Changed](#changed-23)
- [0.1.0 - 2026-09-24](#010---2026-09-24)
  - [Added](#added-16)
  - [Changed](#changed-24)
  - [Fixed](#fixed-16)

## Unreleased

## [0.12.0] - 2026-10-27

### Added

- Add opt-in `check-test-results` with an Xcode-summary adapter, configurable acceptance counts,
  explicit artifact selection and redacted diagnostics.
- Add `check-swift-boundaries` with consumer-named layers, import/symbol restrictions and shared
  Swift lexical masking.
- Add `check-python-boundaries` with AST-based imports, relative import resolution and alias-aware
  explicit symbols. All result/boundary commands support profiles and text/JSON reporting.

### Changed

- Share boundary policy models, confined input reads and analyzer orchestration through a typed
  protocol while preserving Python AST and Swift lexical dependency semantics.
- Share source/log pattern validation with setting-specific diagnostics for unsafe selections.
- Unify documentation iteration, callable-contract dispatch and post-parse source evaluation; retain
  native declaration types, NumPy/DocC syntax and language-specific parsing failures.
- Clarify Python runtime versus Swift compiler observations, simplify result-adapter dispatch,
  remove redundant boundary aliases and align internal names and docstrings.
- Modernize test suites with isolated policy fixtures, typed language cases, exact diagnostic
  assertions and stronger read-once contracts. Keep unit checks in class suites and shared policy
  tests in the configuration layer; preserve comments, docstring details and complete coverage.

### Fixed

- Correct Python boundary ownership for root-level `src.py` modules without confusing them with a
  `src/` package layout.
- Validate guardrail entry points and their selected profile from one policy snapshot instead of
  rereading configuration during loading.

## [0.11.0] - 2026-10-26

### Added

- Add opt-in `check-swift-policy` with an independent loader, explicit stable compiler selections,
  local version and package-minimum checks, and scoped CI observations without executing Swift. Add
  an optional shared scoped workflow parser for Python while retaining its legacy default.
- Opt-in `check-python-source`, `check-swift-source` and `check-logs` commands with consumer-owned
  policies, existing text/JSON reporting, confined input discovery, and redacted log findings. See
  [source and log checks](docs/source-and-log-checks.md)
- Standardize the Swift command and policy as `check-swift-source` / `swift-source`. Share
  source-size, documentation-width and source-guide checks; add optional Python NumPy and Swift DocC
  callable documentation checks with explicit language-specific syntax limits. Retain shared
  configuration loading and read-only, redacted input handling.
- Separate Python and Swift declaration collection from NumPy/DocC interpretation using shared
  immutable facts. Standardize policy keys as `documentation-width` and `max-file-lines` and use
  consistent limit diagnostics; replace the earlier option names without aliases.

### Changed

- Index missing hosted findings by repository/check when applying approvals and use immutable record
  replacement, preserving evidence, exception scope and expiry-finding order.
- Separate hosted branch-context parsing from API orchestration and reporting while preserving
  required-check unions and the distinction between missing and inaccessible evidence.
- Assemble actionlint compatibility replacements from original source spans in one pass, avoiding
  repeated whole-file copies while preserving anchors, script text and source locations.
- Separate CLI inventory generation and hosted-audit reporting from main dispatch and share format
  option setup, preserving command syntax, output streams and exit behavior.
- Prepare log patterns once per validation and compute relative filenames once per file, retaining
  redacted file/line/rule ordering and one finding per matching rule per line.
- Separate Markdown target validation from source/reference traversal, preserving anchor caching,
  target containment, directory handling and diagnostic order.
- Separate Git header-source inventory from filesystem fallback and reuse ignored-directory sets.
- Rename `tests/unit/configs/` to `tests/unit/config/` to mirror the source package and update
  test module names, contributor commands and current documentation.
- Split hosted repository and exception parsing from loader orchestration, caching expected checks
  once per repository while retaining exact exception scopes and validation order.
- Represent privileged-trigger exceptions with named immutable fields and isolate approval parsing
  from safety configuration loading, preserving tuple semantics and lifecycle diagnostics.
- Separate dependency metadata parsing from comparison orchestration and avoid allocating unused
  upper-bound lists, preserving partial results, failure ordering and both comparison modes.
- Separate committed inventory tree decoding and blob validation/hashing from Git orchestration,
  retaining sorted output, checksums and read-only operation.
- Align Python/Swift command-adapter names and source-dispatch docstring contracts without changing
  command names, policy defaults or language-specific checks.
- Share Python/Swift source-validation orchestration and align per-file `_source_findings`
  contracts, preserving diagnostic order, Python syntax errors and Swift lexical boundaries.
  Document both validators' analysis boundaries and consumer-controlled conventions.
- Separate Swift policy parsing from configuration loading, matching the Python policy boundary;
  clarify immutable settings and propagated exception contracts without changing version rules.
  Separate Python local/workflow findings and clarify Swift observation/read stages, preserving
  diagnostic order, shared metadata reads and language-specific error handling. Clarify each Swift
  setting separately and align loader/path contracts with Python policy documentation. Standardize
  local/workflow helper contracts and correct Swift text-input documentation.
- Align per-declaration documentation checking under `_declaration_findings` and share the
  file-overview diagnostic. Keep Python declaration presence and Swift nominal/member/spacing
  policies separate, preserving diagnostic order and existing callable-contract behavior.
- Align Python and Swift documentation interpreters around `_documentation`, `_parameters` and
  `_section`, using immutable `CallableDocumentation` evidence in shared contract checking. Preserve
  NumPy/DocC syntax, result/exception mappings and language-specific presence/spacing rules.
- Align return/exception analysis under `_requirements` in both declaration collectors using one
  immutable `CallableRequirements` model. Preserve Python annotation/body analysis, generator
  priority and locally caught raises, plus Swift signature-only return and throws/rethrows rules.
- Name parameter-syntax observations consistently in both declaration collectors. Retain native
  Python `ast.arg` nodes and replace Swift positional span tuples with immutable `_ParameterSyntax`
  records, preserving offsets, parameter ordering and nested type/default parsing.
- Align file-overview detection under `_file_overview` in both declaration collectors and group
  language-policy constants consistently. Preserve Python module-docstring and Swift leading-
  comment conventions, including their different treatment of declaration documentation.
- Align callable-signature extraction in both declaration collectors using `_signature` and named,
  immutable `_Signature` records. Keep Python annotation observations separate from body-derived
  requirements and retain Swift lexical boundaries and explicit unsupported-signature markers.
- Give both declaration collectors a single-declaration conversion boundary. Python now converts
  classes and callables through `_declaration`, matching Swift's counterpart; aggregation retains
  discovery order, and docstrings distinguish native AST analysis from lexical signature facts.
- Align Python and Swift declaration collectors around explicit syntax-discovery and declaration-
  construction stages, shared helper-role names, and matching documentation contracts. Preserve
  native AST analysis, bounded Swift lexing and all language-specific source-policy observations.
- Collect actionlint compatibility sources separately from tool execution. Read each automation file
  once and share its text between validation and normalization; reuse the restricted YAML mapping
  parser for both text snapshots and file inputs.
- Separate safety discovery and npm comparison from orchestration. Yield npm findings so drift found
  before malformed data remains visible; avoid repeated guardrail step-shape conversion.
- Separate header-rule and preservation-exception parsing from configuration orchestration,
  retaining first-match order, validation diagnostics and consumer-owned defaults.
- Share Python/Swift source-policy defaults while preserving language-specific opt-ins. Separate
  Swift local and workflow observation collection from comparisons and avoid repeated linear
  searches through CI observations. Compute documentation-width settings once per source file.

### Fixed

- Read template JSON metadata explicitly as UTF-8 so Unicode names and descriptions validate
  consistently regardless of the machine's default text encoding.
- Reject all whitespace in template placeholder refs, including tabs, carriage returns and Unicode
  whitespace, while preserving valid literal tokens and repeated automation discovery patterns.
- Restrict release-version components to ASCII digits, rejecting mixed Unicode digits before
  changelog file inspection while preserving optional `v` prefixes and valid numeric cores.
- Reject log literals containing line separators that cannot match the line-based scanner, including
  trailing separators, instead of silently accepting ineffective diagnostic rules.
- Report malformed Markdown URLs without aborting later links, including inline destinations and
  reference definitions; keep remote checks offline.
- Report orphan template-metadata discovery and companion-inspection errors as redacted findings
  without aborting later files/directories; pins-only mode still skips metadata inspection.
- Report automation-pattern discovery and file-inspection failures without exposing exception text
  or aborting independent patterns, in both full-contract and pins-only modes.
- Preserve carriage returns and line feeds in Git-discovered header filenames by capturing binary
  NUL-delimited paths, preventing files from being silently omitted during text-mode decoding.
- Redact malformed source-inventory blob headers, including invalid sizes, from failure messages.
- Report safety workflow discovery errors without aborting independent workflow and npm checks.
- Canonicalize package names in exact dependency comparisons so equivalent case and separator
  spellings do not cause false mismatches; retain version, extras, marker and URL comparisons.
- Treat quoted Python `None`, `NoReturn` and `Never` return annotations like their unquoted forms
  when checking documentation, while still requiring documentation for explicit value returns.
- Return a redacted diagnostic when a selected log root cannot resolve.

## [0.10.0] - 2026-10-25

### Added

- Add explicit `source-inventory --revision` generation in plain JSON or source-only SPDX 2.3,
  sharing committed-blob collection, revision identity and checksum logic without consumer writes.
  Reject unsupported submodules, preserve symlink text, ignore checkout edits and require a
  top-level working-tree root. Keep generation outside check profiles and release approval.

## [0.9.1] - 2026-10-24

### Added

- Add independently runnable consumer examples under `examples/swift/`, `examples/python/` and
  `examples/cdk/`, with one explicit Popo profile shared by Make, pre-commit and a complete CI
  workflow. Shorten the original Swift example path and retain conventional Markdown filenames.

### Changed

- Keep Python minimum dependency constraints and exact Python CDK pins distinct; both examples check
  declared Python/tool policy. Application tests and local CDK synthesis remain separate from
  credential-free, read-only guardrail execution.
- Parameterize actual Make, installed Git-hook and workflow-command acceptance tests across all
  three examples using wheels and sdists. Detect policy failures, entry-point drift and unchanged
  source bytes; retain deterministic CLI coverage and Python/CDK declaration-drift tests.
- Share installed-artifact helpers and include all e2e suites in `make test-installation`; keep
  POSIX example execution separate from Windows native-CLI coverage.
- Consolidate guardrail drift cases and hook metadata setup; reuse UTF-8 fixture writers and
  strengthen configuration-error and input-preservation assertions.
- Extend dependency-policy cases across both comparison modes and automation configuration cases
  across standalone and Python metadata sources. Isolate header-policy tests from installed Git.

### Fixed

- Inspect actionlint's temporary source view during mocked execution and cover tool failure and
  launch cleanup; restore the launch test's workflow fixture dependency.
- Correct source and test docstrings for exception propagation, returned diagnostics, fixture scope,
  pin syntax, header handling, configuration guarantees, and serialization behavior. Document
  existing URL-parsing and external-metadata path errors without changing runtime behavior.

## [0.9.0] - 2026-10-24

### Added

- Add standalone `popo.toml`, explicit offline check selection and named profiles so Swift, CDK and
  other consumers can use shared checks without Python project metadata; retain legacy defaults.
- Add `explain` for check-selection provenance and versioned JSON results for native offline checks.
  Keep individual check identities and continue after per-domain configuration failures.
- Add opt-in `check-guardrail-parity` to inspect an explicit Make/profile, whole-repository local
  pre-commit hook and CI-step invocation contract without executing consumer commands.

### Changed

- Separate native check adapters from CLI parsing and share their dispatch registry; run selected
  checks directly instead of rebuilding and reparsing the CLI. Preserve command defaults and
  diagnostic contracts, and collect pre-commit hook matches in one traversal.
- Expand independent default/text/JSON and installed guardrail scenarios for Make, hook and workflow
  drift; share diagnostic and byte-snapshot fixtures. Split Markdown tests by target,
  reference/image and syntax scope while retaining existing cases and documentation.

### Fixed

- Correct Markdown-check coverage, policy-source and reporting descriptions, source ownership,
  hosted-audit guidance, and preparation-time release status; clarify docstrings and dot-file
  headers.
- Keep inspecting Make recipes across non-recipe comments: accept comments before a valid recipe and
  reject extra commands previously hidden after comment separators.
- Align autopep8 with Ruff by ignoring `E203`, preventing commit-time formatting conflicts on
  complex slices.

## [0.8.2] - 2026-10-23

### Fixed

- Backfill the missing 0.8.1 changelog entry and release record, and add the 0.8.2 release record
  and archive navigation. Preserve the immutable 0.8.1 tag and its missing-record validation gap.

## [0.8.1] - 2026-10-23

### Changed

- Stream XML preamble and line-comment header scanning while preserving accepted syntax and consumer
  directives.
- Read shared Python-policy package/Ruff metadata once and report each shared input failure once.
- Share safe YAML loading and iterative mapping traversal across automation, actionlint and safety
  checks. Preserve nested traversal order and avoid recursion-limit failures in parsed structures.
- Consolidate CLI parser setup and configuration string-array validation, modernize type aliases,
  and complete class-based unit suites while preserving consumer-specific policy differences.
- Split hosted configuration, adapter and CLI tests by scope and share hosted-evidence fixtures.
- Exercise both installed CLI entry points for passing and failing Markdown/file policies, verify
  consumer files remain unchanged, and match reported versions to artifact filenames.

### Fixed

- Keep dangling header symlinks in discovery so containment checks run before preservation
  exceptions. Report required-file resolution/inspection errors without skipping later paths.
- Reject unresolved workflow Python-version references even when another declaration is valid;
  report unresolved expressions as unsupported versions instead of silently skipping them.
- Fix safety-check crashes on recursive YAML aliases and duplicate shell-interpolation diagnostics
  for mappings reused through aliases; continue inspecting later policy violations.
- Report malformed dependency project tables as diagnostics instead of raising an attribute error.
- Require safety-exception expiry strings in canonical `YYYY-MM-DD` form; compact and ISO week dates
  are rejected. Add regression coverage for malformed policy, hosted evidence and CLI paths.

## [0.8.0] - 2026-10-23

### Added

- Add opt-in `check-required-files` and `check-file-headers` commands with consumer-owned paths,
  identity templates, comment formats, executable directives and reasoned preservation exceptions.
  Configured file checks also participate in `check-all`; existing consumers remain unchanged.

### Changed

- Align local Ruff-hook dependency bounds with the existing development extra.

## [0.7.0] - 2026-10-22

### Added

- Extend Markdown validation to local inline images, undefined full/collapsed reference labels and
  conflicting reference destinations; ignore inline code and HTML comments without losing source
  line numbers. Keep external destinations offline and local targets within the repository.

### Changed

- Accept verb-oriented `release/prepare-MAJOR.MINOR.PATCH` candidate names while preserving dated
  release-record requirements and the existing release/hotfix naming forms.

## [0.6.6] - 2026-10-08

### Changed

- Replace sixteen local engineering guides, policy files, indexes, and blank templates with Dagitali
  Engineering equivalents; shared Markdown links follow the organization's `main` branch.
- Consolidate Popo-specific setup, recovery, branch routing, release validation, and publication
  safeguards in `CONTRIBUTING.md`; retain community-health files, agent instructions, product
  contracts, test layout, and release history.
- Update documentation navigation and policy references, and record shared-source ownership and
  maintenance boundaries in `docs/engineering.md`.

## [0.6.5] - 2026-10-08

### Removed

- Remove the local pull request template in favor of Dagitali's organization default, update
  contributor references, and preserve Popo's packaging and read-only validation requirements in
  contributor guidance; hosted template injection remains to be verified after integration.

## [0.6.4] - 2026-10-07

### Removed

- Remove local issue forms and chooser configuration to adopt Dagitali's organization defaults;
  retain blank issues, version/environment context, and Popo-specific support/security policies
  while adopting bracketed titles, optional selectors, and shared reporting navigation. Point
  contributor/support links to the hosted chooser; displayed inheritance remains to be verified.

## [0.6.3] - 2026-10-07

### Fixed

- Backfill the missing 0.6.2 changelog entry and release record, and add matching 0.6.3 records to
  satisfy release validation while preserving the immutable 0.6.2 tag.

## [0.6.2] - 2026-10-07

### Fixed

- Backfill 0.6.1 release notes, changelog history, and archive navigation; align README and
  historical release status with existing tags while preserving recorded validation gaps.

## [0.6.1] - 2026-10-07

### Changed

- Update Commitizen pre-commit hooks from v4.19.0 to v4.19.1 and mypy hooks from v2.3.1 to v2.4.0
  through Dependabot PR #5, preserving hook settings and Popo runtime behavior.

## [0.6.0] - 2026-10-07

### Added

- Add opt-in `check-repository-safety` and `[tool.popo.safety]` for reviewed privileged-trigger
  exceptions, direct event-data shell interpolation, and npm manifest/lockfile root consistency.
  Include configured safety checks in `check-all` without network access or command execution; full
  dependency-graph validation and workflow trust review remain separate requirements.

## [0.5.2] - 2026-10-06

### Changed

- Normalize historical release records and UTC dates; centralize shared release guidance and link
  versioned highlights to this changelog while preserving historical validation evidence.
- Target `develop` for Dependabot version-update pull requests across GitHub Actions, Python, and
  pre-commit hooks; security-update pull requests continue targeting the default branch.

### Fixed

- Backfill the missing 0.5.1 release record, archive entry, and dated changelog section.

## [0.5.1] - 2026-10-06

### Changed

- Update md-toc from 9.0.0 to 9.1.0 and Ruff pre-commit hooks from v0.16.9 to v0.16.10 through
  Dependabot PR #4, preserving existing hook settings and Popo runtime behavior.

## [0.5.0] - 2026-10-06

### Added

- Add opt-in `audit-github-settings` with explicit `[tool.popo.hosted]` consumer expectations for
  security settings, labels, CODEOWNERS, branch protection, and required check contexts.
- Report verified settings, confirmed drift, inaccessible evidence, and approved expiring exceptions
  through sanitized text or JSON output with UTC timestamps and evidence URLs.
- Add `make hosted-audit`, deterministic regression tests, and configuration and adoption guidance.
  The command requires authenticated `gh` access to github.com, uses only GET requests, and remains
  separate from offline `check-all` and `make check`; no hosted settings are changed.

## [0.4.1] - 2026-10-04

### Fixed

- Backfill the missing 0.4.0 release record, archive entry, and dated changelog section.

## [0.4.0] - 2026-10-04

### Added

- Recognize revision-free `$/` action/workflow references natively in pin and automation contract
  validation, including containment, target, and input checks without source copying.
- Add `check-actionlint` for read-only compatibility with older actionlint versions. Use parsed YAML
  locations and a disposable automation-only view, retain source diagnostics and exact tool exit
  statuses, and keep external-tool execution separate from `check-all`.

## [0.3.7] - 2026-10-01

### Changed

- Refactor tests into independent parameterized scenarios, simplify fixture naming and repeated
  setup, group automation contracts into cohesive test classes, and expand automation regression
  coverage. Prevent inherited Make overrides from leaking into tests, reject incomplete artifact
  sets before Twine validation, and limit symlink skips to platform restrictions while preserving
  CLI behavior and test-layer boundaries.
- Prefix unit, integration, e2e, and meta test modules with `test_u_`, `test_i_`, `test_e_`, and
  `test_m_`, respectively, to reduce cross-layer namespace collisions; update Make targets, module
  docstrings, and test-path references while preserving test names and importlib discovery.

## [0.3.6] - 2026-10-01

### Added

- Add a read-only PR and merge-queue gate for dated changelog sections and matching release
  documents, with explicit candidate-version validation on release/hotfix branches. Document the
  required-check transition for `main` and `develop`; hosted enforcement requires activation after
  successful hosted validation.
- Add 12 release-record regression scenarios and synchronize contributor, workflow, and branch
  protection guidance. Backfill the 0.3.5 release document and dated changelog section without
  changing its existing tag or claiming historical artifact validation.
- No CLI, consumer-configuration, runtime dependency, or publication behavior changes.

## [0.3.5] - 2026-10-01

### Changed

- Standardize source and test docstrings with NumPy-style contracts, Sphinx references, inline
  parameter literals, and the 79-character line convention; preserve executable behavior.
- Document fixture isolation, subprocess timeouts, propagated errors, scenario inputs, and
  automation-loader validation boundaries.

## [0.3.4] - 2026-10-01

### Changed

- Update the Commitizen pre-commit hook from `v4.18.1` to `v4.19.0` and Ruff hooks from `v0.16.8` to
  `v0.16.9` through [PR #3], preserving existing hook stages, arguments, and local checks.
- No runtime dependency, CLI, consumer-configuration, or publication behavior changes.

## [0.3.3] - 2026-09-30

### Changed

- Group unit tests under `checks/` and `configs/` to align with `popo.checks` and `popo.config`,
  preserving test coverage, shared fixtures, and default discovery.
- Separate automation configuration validation from checker tests, correct its shared-helper import,
  and update test-selection guidance and source-to-test references.

## [0.3.2] - 2026-09-30

### Fixed

- Backfill the dated 0.3.1 changelog entry and release document, add the 0.3.2 candidate record, and
  index both versions in the release archive. Preserve the existing 0.3.1 tag and distinguish its
  missing release entry from validation of this correction.
- No runtime, configuration, dependency, workflow, or publication behavior changes.

## [0.3.1] - 2026-09-30

### Changed

- Link onboarding and consumer-adoption guidance directly from the README, expand upstream format
  and automation references, and clarify design, roadmap, and installation-validation guidance
  without changing runtime behavior or project policies.
- Clarify consumer integration and repository automation boundaries, configuration-change review,
  and support-topic navigation. Repair Code of Conduct attribution links and the pytest reference
  while retaining existing compatibility and publication policies.
- Extend reusable root guidance with distinct workflow roles, agent Git/release responsibilities,
  release-classification criteria, upstream tooling references, and action-pin/version
  troubleshooting. Preserve existing anchors, configurable routing, publication safeguards, and
  support boundaries.
- Align root documentation coverage with reusable project guidance: add architecture, design,
  workflow, security, support, conduct, learnings, references, and roadmap guides. Expand agent
  orientation and documentation ownership while preserving read-only checking, configurable routing,
  existing validation gates, and opt-in publication.

## [0.3.0] - 2026-09-30

### Added

- Add `check-automation-contracts` and its `--pins-only` mode, with optional consumer-owned
  `[tool.popo.automation]` configuration and opt-in `check-all` integration. Validate local
  workflow/action inputs, composite steps, YAML, template metadata, and reference pins without
  executing automation or fetching remote code. Scope configured placeholders to self-targeting
  templates; preserve the existing action-pin command.
- Add PyYAML as a runtime dependency and its matching minimum constraint.

### Changed

- Organize configuration into the `popo.config` subpackage with shared TOML loading and separate
  dependency, Python-policy, and automation modules. Preserve existing `popo.config` exports, policy
  defaults, and opt-in automation checks.
- Expand configuration, automation, CLI, distribution-content, and clean-install regression
  coverage.

### Fixed

- Repair changelog version links, source references, and the PR status badge; synchronize
  configuration guidance with automation-contract settings and opt-in aggregate checks.

## [0.2.4] - 2026-09-27

### Changed

- Standardize historical release records with consistent scope descriptions, tagged dates, and
  verified tag status while preserving their preparation-time validation evidence.
- Link versioned notes to dated changelog entries and the release archive without changing runtime,
  CLI, dependency, workflow, or publication behavior.

## [0.2.3] - 2026-09-27

### Changed

- Align agent guidance with existing versioning, public API, docstring, deterministic-test, and
  action-pinning conventions, and map change types to focused validation commands.
- Distinguish default source checks from artifact creation and clean-installation gates, including
  the need to exercise build-on-demand fixtures rather than only prebuilt artifacts.
- Link the release-note template to the release archive and distinguish candidate evidence from
  tagging and publication.
- Standardize release-archive entries with evidence-backed dates and consistent separators; label
  planned preparation dates explicitly and document the convention for future entries.
- Expand shared pytest fixture and hook docstrings with inputs, results, exceptions, side effects,
  and isolation boundaries without changing test or runtime behavior.

## [0.2.2] - 2026-09-26

### Changed

- Expand Python docstrings for configuration models and loading, CLI dispatch and exit statuses,
  dependency parsing, Markdown anchors and fences, Python-policy resolution, action pinning,
  changelog validation, automation discovery, and package version lookup.
- Clarify defaults, path resolution, return values, propagated exceptions, and parser limitations
  without changing executable behavior, consumer configuration, or dependency requirements.

## [0.2.1] - 2026-09-26

### Fixed

- Fix the artifact fixture's build option from `--out-dir` to `--outdir`, restoring distribution and
  clean-installation tests that build their own wheel and source distribution.

## [0.2.0] - 2026-09-26

### Added

- Resolve block-list Python-version matrices in workflow policy checks alongside inline lists,
  validating each resolved version against the consumer's configured support range.
- Accept whitespace-delimited inline comments in dependency requirements and constraint files while
  preserving URL fragments and rejecting installer directives.
- Validate Markdown reference-link destinations and explicit HTML anchors, including unused
  definitions; broken reference destinations now fail repository checks instead of being ignored.
- Accept plain links to existing directories without requiring a README; retain README anchor
  resolution for directory links with fragments.
- Run the existing local quality gate at the installed pre-push hook stage, using Make's interpreter
  selection rather than requiring a bare `python` executable.
- Expand the public README and documentation with configuration and testing references, onboarding
  and adoption tutorials, API and architecture guidance, release and change-management playbooks,
  incident and required-check runbooks, and reusable evidence and task templates.

### Changed

- Describe the package without restricting consumer projects to Python and expose the maintained
  documentation URL in distribution metadata.
- Document the minimum-dependency fixture and shared formatting rules; ignore common
  operating-system metadata and additional coverage outputs without importing cloud-specific
  configuration.
- Raise development-tool minimum versions and align managed Ruff hooks with `ruff>=0.16.9,<0.17`;
  retain Python `>=3.13,<3.15` and the runtime dependency `packaging>=26.3,<27`.
- Expand checker regression coverage and public docstrings, and clarify the MIT terms in `NOTICE`
  without changing the license.

### Fixed

- Exclude vendored `node_modules` Markdown from source discovery and match build exclusions by path
  component so maintained paths such as `docs/building.md` are no longer silently skipped.
- Reject local Markdown destinations that resolve outside the selected repository, including encoded
  parent paths and symlinked targets, while retaining valid in-repository parent links.
- Validate link fragments only for Markdown targets, avoiding decoding failures on binary files;
  reuse Markdown anchors within each check without retaining stale results between runs.
- Reject remote action references with a missing action name even when their revision is a full
  commit SHA; preserve local-action and container-reference exemptions.
- Ignore links and headings inside fenced Markdown code examples, including mixed or shorter
  embedded fence markers, while preserving source line numbers in real-link diagnostics.

## [0.1.5] - 2026-09-24

### Added

- Add the 0.1.5 release record and update the release archive.

### Removed

- Remove `.github/README.md` so GitHub displays the root `README.md` as the repository homepage
  overview rather than the automation notes.

## [0.1.4] - 2026-09-24

### Added

- Add the 0.1.4 release record and synchronize the release archive with the corrected history.

### Fixed

- Add the missing dated 0.1.3 changelog entry and prepare the 0.1.4 entry required by CD's
  release-changelog gate, without moving or reusing the existing 0.1.3 tag.

## [0.1.3] - 2026-09-24

### Changed

- Update the Commitizen pre-commit hook from v4.18.0 to v4.18.1 and Ruff hooks from v0.16.7 to
  v0.16.8.
- This entry was added retrospectively in 0.1.4. The original 0.1.3 tagged tree lacked a dated
  changelog section, causing CD validation to fail; this correction does not change that tag.

## [0.1.2] - 2026-09-24

### Changed

- Document release preparation and distinguish candidate validation from tagged artifact evidence.

### Removed

- Remove the obsolete Dependabot fixture-exclusion test that failed with `KeyError:
  'exclude-paths'`.

### Fixed

- Correct contributor and release guidance to allow Dependabot fixture updates while requiring
  matching metadata lower bounds before merging; retain the dependency-consistency check.

## [0.1.1] - 2026-09-24

### Added

- Add regression coverage for synchronized minimums, older and newer mismatched pins, and an
  intended Dependabot fixture exclusion. The missing configuration and obsolete exclusion test are
  addressed by 0.1.2.

### Changed

- Raise the minimum supported `packaging` version to 26.3 and synchronize the lowest-dependency test
  pin. Versions below 26.3 are no longer supported; the upper bound remains below 27.

## [0.1.0] - 2026-09-24

### Added

- Explicit virtual-environment creation, runtime/development installation, setup alias, and
  environment inspection targets that refuse to replace existing environments.
- Discoverable Make help, focused policy checks, common formatting/build/test aliases, and
  overridable tool, packaging, and distribution-test commands while preserving the existing local
  quality gate.
- Configurable PR routing, tagged release validation with opt-in GitHub publication, and manual
  cross-platform disposable installation workflows.
- Lowest/newest dependency CI, cross-platform distribution tests, and branch-coverage reporting.
- Standalone CycloneDX SBOM generation and manual runtime-dependency vulnerability auditing, with
  isolated tools, bounded permissions, and short-lived report artifacts.
- Repository self-check and distribution validation Make targets, with artifact tests in CI.
- Initial `popo` command-line interface.
- Checks for Markdown links, GitHub Actions pins, dependency boundaries, Python-version policy, and
  release changelog entries.
- Declarative configuration through `[tool.popo]` in `pyproject.toml`.

### Changed

- Class-based pytest suites with reusable fixtures, independent installed-CLI scenarios, and
  expanded negative-path coverage for configuration, policy, and command dispatch.
- Scope-based test layers, shared artifact fixtures, automatic layer markers, and focused
  unit/integration Make targets; distribution validation remains opt-in.
- Explicit package discovery boundaries and shared pytest, Ruff, and coverage configuration
  conventions, including importlib-based test imports, retaining CLI-specific dependencies and test
  scope.
- Explicit workflow schema comments and updated workflow responsibilities and boundaries.
- Generalized GitHub issue and pull request templates, file headers, dependency-update
  configuration, release-note templates, and portable contributor guidance.
- Shared Python setup action, bounded CI jobs, merge-group/manual validation, and full-history
  checkouts for Git-derived package versions.
- Editor and Git text conventions, issue and pull request templates, and opt-in pre-commit hooks
  adapted from `aws-cdk-static-site`.
- Checker regression cases and wheel/source-distribution contract and clean-install tests.
- Complete the Python module rename to `popo` in packaging, development tooling, documentation, and
  clean-distribution tests.

### Fixed

- Pre-commit no longer requires a bare `python` on PATH: Popo checks use Make and filename-scoped
  Ruff hooks use a managed Python environment.
- Make selects the managed Python environment when no virtual environment is active, so local tests
  find the editable package without a `PYTHONPATH` workaround.
- Source tests and Make checks resolve the local `src` tree explicitly, including on macOS when
  hidden `.pth` files prevent editable-install path discovery.


[release notes archive]: docs/releases/README.md
[reading guide]: docs/releases/README.md#reading-the-records
[0.1.0]: docs/releases/v0.1.0.md
[0.1.1]: docs/releases/v0.1.1.md
[0.1.2]: docs/releases/v0.1.2.md
[0.1.3]: docs/releases/v0.1.3.md
[0.1.4]: docs/releases/v0.1.4.md
[0.1.5]: docs/releases/v0.1.5.md
[0.2.0]: docs/releases/v0.2.0.md
[0.2.1]: docs/releases/v0.2.1.md
[0.2.2]: docs/releases/v0.2.2.md
[0.2.3]: docs/releases/v0.2.3.md
[0.2.4]: docs/releases/v0.2.4.md
[0.3.0]: docs/releases/v0.3.0.md
[0.3.1]: docs/releases/v0.3.1.md
[0.3.2]: docs/releases/v0.3.2.md
[0.3.3]: docs/releases/v0.3.3.md
[0.3.4]: docs/releases/v0.3.4.md
[0.3.5]: docs/releases/v0.3.5.md
[0.3.6]: docs/releases/v0.3.6.md
[0.3.7]: docs/releases/v0.3.7.md
[0.4.0]: docs/releases/v0.4.0.md
[0.4.1]: docs/releases/v0.4.1.md
[0.5.0]: docs/releases/v0.5.0.md
[0.5.1]: docs/releases/v0.5.1.md
[0.5.2]: docs/releases/v0.5.2.md
[0.6.0]: docs/releases/v0.6.0.md
[0.6.1]: docs/releases/v0.6.1.md
[0.6.2]: docs/releases/v0.6.2.md
[0.6.3]: docs/releases/v0.6.3.md
[0.6.4]: docs/releases/v0.6.4.md
[0.6.5]: docs/releases/v0.6.5.md
[0.6.6]: docs/releases/v0.6.6.md
[0.7.0]: docs/releases/v0.7.0.md
[0.8.0]: docs/releases/v0.8.0.md
[0.8.1]: docs/releases/v0.8.1.md
[0.8.2]: docs/releases/v0.8.2.md
[0.9.0]: docs/releases/v0.9.0.md
[0.9.1]: docs/releases/v0.9.1.md
[0.10.0]: docs/releases/v0.10.0.md
[PR #3]: https://github.com/Dagitali/popo/pull/3
[Keep a Changelog]: https://keepachangelog.com/en/1.1.0/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html
