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

Use the [changelog] for concise change history and the [release policy] for validation and
publication safeguards.

- [0.1 Series](#01-series)
- [Initial Scaffold](#initial-scaffold)
- [Maintaining the Archive](#maintaining-the-archive)

## 0.1 Series

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

The changelog records `0.1.0` under its dated release section. Changes after `0.1.0` belong in
`Unreleased` until the next release is prepared.

[release notes template]: ../../.github/RELEASE-NOTES-TEMPLATE.md
[changelog]: ../../CHANGELOG.md
[release policy]: ../../RELEASE-POLICY.md
[v0.0.0]: v0.0.0.md
[v0.1.0]: v0.1.0.md
