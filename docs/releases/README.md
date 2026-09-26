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

- [0.2 Series](#02-series)
- [0.1 Series](#01-series)
- [Initial Scaffold](#initial-scaffold)
- [Maintaining the Archive](#maintaining-the-archive)

## 0.2 Series

- [v0.2.0] — planned: Expand repository checks, tighten validation, and align reusable contributor
  tooling and documentation.

## 0.1 Series

- [v0.1.5]: Display the root README on the repository homepage.
- [v0.1.4] — 2026-09-24: Correct dated release history and restore the changelog gate for the new
  tag.
- [v0.1.3 changelog] — 2026-09-24: Update Commitizen and Ruff hooks; tagged CD validation failed
  because the dated entry was missing. The entry is backfilled in 0.1.4.
- [v0.1.2] - 2026-09-24: Remove the obsolete Dependabot exclusion test and correct dependency
  guidance.
- [v0.1.1] — 2026-09-24: Align the `packaging` minimum at 26.3.
- [v0.1.0] — 2026-09-24: Initial repository-policy CLI and validation workflows.

## Initial Scaffold

- [v0.0.0]: Initial repository shell; not an installable CLI package.

## Maintaining the Archive

1. Create `docs/releases/vMAJOR.MINOR.PATCH.md` for an agreed release candidate using the [release
   notes template]. Mark untagged candidates as planned; do not infer a release number from a
   development build or a fallback version.
2. Reconcile scope with the candidate's changes and changelog. Preserve the template's applicable
   compatibility, support, validation, publication, rollback, and follow-up sections.
3. Record the exact candidate commit and distinguish completed checks from pending checks. Never
   transfer current-checkout validation results to a historical tag.
4. Add the record to this index, newest first. Keep reference definitions sorted by destination.
5. Run `make docs-markdown`. Before release, complete the separate gates in the [release policy].

The current CD workflow generates GitHub Release notes; it does not automatically consume these
Markdown records. Keep published notes consistent with the reviewed record when publication is
authorized. Creating documentation does not authorize tagging or publishing.

The changelog includes a dated `0.2.0` candidate section. Changes outside that candidate belong in
`Unreleased`; the candidate date does not establish publication.

[release notes template]: ../../.github/RELEASE-NOTES-TEMPLATE.md
[changelog]: ../../CHANGELOG.md
[v0.1.3 changelog]: ../../CHANGELOG.md#013---2026-09-24
[release policy]: ../../RELEASE-POLICY.md
[release playbook]: ../playbooks/release.md
[v0.0.0]: v0.0.0.md
[v0.1.0]: v0.1.0.md
[v0.1.1]: v0.1.1.md
[v0.1.2]: v0.1.2.md
[v0.1.4]: v0.1.4.md
[v0.1.5]: v0.1.5.md
[v0.2.0]: v0.2.0.md
