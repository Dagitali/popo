<!--
README.md
popo/docs/releases

Copyright © 2026 Dagitali LLC. All rights reserved.

Index and maintenance guidance for release-aligned records.

Maintainer Notes
- Index records newest first; distinguish planned candidates from tagged versions.
- Record evidence, not assumed publication or validation outcomes.
-->

# Release Notes Archive

This archive indexes Popo's release-aligned records, newest first. These documents preserve change
scope, compatibility, validation, publication, rollback, and follow-up details where applicable. A
committed record or local tag does not establish that a GitHub Release or PyPI package exists.

Use the [changelog] for concise change history, the [release playbook] for preparation, and the
[release policy] for validation and publication safeguards.

- [0.5 Series](#05-series)
- [0.4 Series](#04-series)
- [0.3 Series](#03-series)
- [0.2 Series](#02-series)
- [0.1 Series](#01-series)
- [Initial Scaffold](#initial-scaffold)
- [Maintaining the Archive](#maintaining-the-archive)

## 0.5 Series

- [v0.5.0] — planned, prepared 2026-10-06: Add opt-in, read-only GitHub settings auditing with
  explicit consumer expectations, sanitized reports, and expiring approved exceptions.

## 0.4 Series

- [v0.4.1] — planned, prepared 2026-10-04: Backfill the 0.4.0 release record and dated changelog
  history while preserving the original tag and historical evidence boundaries.
- [v0.4.0] — 2026-10-04: Add native self-repository reference validation and read-only actionlint
  compatibility; retrospective record added after tagging.

## 0.3 Series

- [v0.3.7] — 2026-10-01: Refactor test naming, classes, parameterized scenarios, and fixtures;
  strengthen subprocess isolation and artifact validation.
- [v0.3.6] — 2026-10-01: Validate release records in PRs and merge queues, document required-check
  activation, and backfill the 0.3.5 release record.
- [v0.3.5] — 2026-10-01: Complete NumPy-style Python docstrings, add Sphinx references, and document
  the 79-character docstring convention.
- [v0.3.4] — 2026-10-01: Update Commitizen and Ruff pre-commit hooks without changing Popo runtime
  behavior or consumer configuration.
- [v0.3.3] — 2026-09-30: Reorganize checker and configuration unit tests, correct shared-helper
  imports, and synchronize test-layout guidance.
- [v0.3.2] — 2026-09-30: Correct omitted release records and dated changelog history while
  preserving the existing 0.3.1 tag.
- [v0.3.1] — 2026-09-30: Align and generalize root documentation; retrospective record added in
  0.3.2 because the original tag lacked its dated changelog entry and release document.
- [v0.3.0] — 2026-09-30: Add automation-contract validation, reorganize configuration, expand
  regression coverage, and repair documentation references.

## 0.2 Series

- [v0.2.4] — 2026-09-27: Standardize historical release records and evidence boundaries.
- [v0.2.3] — 2026-09-27: Align contributor validation guidance, release records,
  and test-fixture documentation.
- [v0.2.2] — 2026-09-26: Expand source docstrings and clarify checker contracts without behavior
  changes.
- [v0.2.1] — 2026-09-26: Correct the build option used by distribution and clean-installation tests.
- [v0.2.0] — 2026-09-26: Expand repository checks, tighten validation, and align reusable
  contributor tooling and documentation.

## 0.1 Series

- [v0.1.5] — 2026-09-24: Display the root README on the repository homepage.
- [v0.1.4] — 2026-09-24: Correct dated release history and restore the changelog gate for the new
  tag.
- [v0.1.3] — 2026-09-24: Update Commitizen and Ruff hooks; tagged CD validation failed because the
  dated entry was missing. The entry is backfilled in 0.1.4.
- [v0.1.2] — 2026-09-24: Remove the obsolete Dependabot exclusion test and correct dependency
  guidance.
- [v0.1.1] — 2026-09-24: Align the `packaging` minimum at 26.3.
- [v0.1.0] — 2026-09-24: Initial repository-policy CLI and validation workflows.

## Initial Scaffold

- [v0.0.0] — 2026-09-21: Initial repository shell; not an installable CLI package.

## Maintaining the Archive

1. Create `docs/releases/vMAJOR.MINOR.PATCH.md` for an agreed release candidate using the [release
   notes template]. Mark untagged candidates as planned; do not infer a release number from a
   development build or a fallback version.
2. Reconcile scope with the candidate's changes and changelog. Preserve the template's applicable
   compatibility, support, validation, publication, rollback, and follow-up sections.
3. Record the candidate tag without embedding a commit SHA, and distinguish completed checks from
   pending checks. Never transfer current-checkout validation results to a historical tag.
4. Add the record to this index, newest first, using `version — YYYY-MM-DD: summary` with the date
   from the changelog or verified release record. For untagged candidates, use `version — planned,
   prepared YYYY-MM-DD: summary`; if no date is established, use `undated` rather than inventing
   one. Keep reference definitions sorted by destination.
5. Run `make docs-markdown`. Before release, complete the separate gates in the [release policy].

The current CD workflow generates GitHub Release notes; it does not automatically consume these
Markdown records. Keep published notes consistent with the reviewed record when publication is
authorized. Creating documentation does not authorize tagging or publishing.

Keep changes after the latest dated changelog entry in `Unreleased` until the next candidate is
prepared. A dated entry or tag does not establish artifact publication.

[release notes template]: ../../.github/RELEASE-NOTES-TEMPLATE.md
[changelog]: ../../CHANGELOG.md
[release policy]: ../../RELEASE-POLICY.md
[release playbook]: ../playbooks/release.md
[v0.0.0]: v0.0.0.md
[v0.1.0]: v0.1.0.md
[v0.1.1]: v0.1.1.md
[v0.1.2]: v0.1.2.md
[v0.1.3]: v0.1.3.md
[v0.1.4]: v0.1.4.md
[v0.1.5]: v0.1.5.md
[v0.2.0]: v0.2.0.md
[v0.2.1]: v0.2.1.md
[v0.2.2]: v0.2.2.md
[v0.2.3]: v0.2.3.md
[v0.2.4]: v0.2.4.md
[v0.3.0]: v0.3.0.md
[v0.3.1]: v0.3.1.md
[v0.3.2]: v0.3.2.md
[v0.3.3]: v0.3.3.md
[v0.3.4]: v0.3.4.md
[v0.3.5]: v0.3.5.md
[v0.3.6]: v0.3.6.md
[v0.3.7]: v0.3.7.md
[v0.4.0]: v0.4.0.md
[v0.4.1]: v0.4.1.md
[v0.5.0]: v0.5.0.md
