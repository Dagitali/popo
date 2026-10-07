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
scope, compatibility, validation, rollback, and follow-up details where applicable.

Use the [changelog] for concise change history, the [release playbook] for preparation, and the
[release policy] for validation and publication safeguards.

- [0.6 Series](#06-series)
- [0.5 Series](#05-series)
- [0.4 Series](#04-series)
- [0.3 Series](#03-series)
- [0.2 Series](#02-series)
- [0.1 Series](#01-series)
- [Initial Scaffold](#initial-scaffold)
- [Reading the Records](#reading-the-records)
  - [Evidence Boundaries](#evidence-boundaries)
  - [Release Operations](#release-operations)
- [Maintaining the Archive](#maintaining-the-archive)

## 0.6 Series

- [v0.6.1] — 2026-10-07: Commitizen and mypy hook updates; retrospective record.
- [v0.6.0] — 2026-10-07: Opt-in repository safety checks.

## 0.5 Series

- [v0.5.2] — 2026-10-06: Dependabot routing and release-history maintenance.
- [v0.5.1] — 2026-10-06: md-toc and Ruff hook updates; retrospective record.
- [v0.5.0] — 2026-10-06: Opt-in GitHub settings audit.

## 0.4 Series

- [v0.4.1] — 2026-10-05: Backfill 0.4.0 release history.
- [v0.4.0] — 2026-10-05: Self-repository references and actionlint compatibility;
  retrospective record.

## 0.3 Series

- [v0.3.7] — 2026-10-02: Test-suite refactoring and artifact isolation.
- [v0.3.6] — 2026-10-01: PR release-record validation and 0.3.5 backfill.
- [v0.3.5] — 2026-10-01: Python docstring completion and conventions.
- [v0.3.4] — 2026-10-01: Commitizen and Ruff hook updates.
- [v0.3.3] — 2026-09-30: Unit-test organization and shared imports.
- [v0.3.2] — 2026-09-30: Backfill 0.3.1 release history.
- [v0.3.1] — 2026-09-30: Root documentation alignment; retrospective record.
- [v0.3.0] — 2026-09-30: Automation contracts and configuration domains.

## 0.2 Series

- [v0.2.4] — 2026-09-27: Historical release-record standardization.
- [v0.2.3] — 2026-09-27: Contributor and test documentation alignment.
- [v0.2.2] — 2026-09-26: Source docstrings and checker contracts.
- [v0.2.1] — 2026-09-26: Artifact-build option correction.
- [v0.2.0] — 2026-09-26: Expanded repository validation and contributor tooling.

## 0.1 Series

- [v0.1.5] — 2026-09-24: Root README selection on GitHub.
- [v0.1.4] — 2026-09-24: Backfill 0.1.3 release history.
- [v0.1.3] — 2026-09-24: Commitizen and Ruff hook updates; retrospective record.
- [v0.1.2] — 2026-09-24: Obsolete Dependabot test removal.
- [v0.1.1] — 2026-09-24: Coordinated packaging minimum and fixture.
- [v0.1.0] — 2026-09-24: Initial repository-policy CLI.

## Initial Scaffold

- [v0.0.0] — 2026-09-21: Repository scaffold; no installable CLI.

## Reading the Records

The [changelog] owns concise, version-specific highlights. This index provides navigation and
release status; versioned records own detailed scope, compatibility, recorded validation,
limitations, and rollback considerations. Link to the owning document rather than copying its full
guidance. The initial scaffold has no dated changelog section and records its highlights here.

### Evidence Boundaries

This index and tagged introductions use UTC dates verified from annotated Git tag metadata,
consistent with the [published tags] page. Changelog dates may reflect original preparation dates.
Preparation dates and results describe the checkout tested at that time. Pending historical
checklists are not proof that the eventual tagged artifacts passed. Retrospective corrections
describe maintained history without modifying the original tagged tree. Neither a document nor a tag
establishes hosted cross-platform validation, artifact integrity, or publication. Each record
retains its specific completed checks, failures, skipped checks, and evidence gaps.

### Release Operations

The [release policy] owns validation and publication safeguards; the [release playbook] owns
preparation and closeout steps. The current workflows validate tags and make GitHub publication
opt-in; they do not publish to PyPI. Documentation changes do not authorize tagging, publication, or
hosted settings changes. Preserve existing tags and use reviewed follow-up releases for fixes.
Versioned deployment sections describe only release-specific effects and rollback considerations.

## Maintaining the Archive

1. Create `docs/releases/vMAJOR.MINOR.PATCH.md` for an agreed release candidate using the [release
   notes template]. Mark untagged candidates as planned; do not infer a release number from a
   development build or a fallback version.
2. Reconcile scope with the candidate's changes and changelog. Preserve the template's applicable
   compatibility, support, validation, publication, rollback, and follow-up sections.
3. Record the candidate tag without embedding a commit SHA, and distinguish completed checks from
   pending checks. Never transfer current-checkout validation results to a historical tag.
4. Add the record to this index, newest first, using `version — YYYY-MM-DD: summary` with the date
   from verified tag metadata in UTC for tagged releases. For untagged candidates, use `version —
   planned, prepared YYYY-MM-DD: summary`; if no date is established, use `undated` rather than
   inventing one. Keep reference definitions sorted by destination.
5. Run `make docs-markdown`. Before release, complete the separate gates in the [release policy].

The current CD workflow generates GitHub Release notes; it does not automatically consume these
Markdown records. Keep published notes consistent with the reviewed record when publication is
authorized.

Keep changes after the latest dated changelog entry in `Unreleased` until the next candidate is
prepared.

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
[v0.5.1]: v0.5.1.md
[v0.5.2]: v0.5.2.md
[v0.6.0]: v0.6.0.md
[v0.6.1]: v0.6.1.md
[published tags]: https://github.com/Dagitali/popo/tags
