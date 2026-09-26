<!--
release.md
popo/docs/playbooks

Copyright © 2026 Dagitali LLC. All rights reserved.

Release preparation, evidence, publication boundaries, and closeout checklist.

Maintainer Notes
- Follow RELEASE-POLICY.md; this checklist does not authorize external operations.
- Preserve tags and distinguish local builds from hosted release validation.
-->

# Release Playbook

Use the [release policy] as the authority for version validation, artifacts, and publication.
The [contributor checklist] explains the local preparation workflow.

- [Prepare](#prepare)
- [Validate](#validate)
- [Tag and Publish](#tag-and-publish)
- [Close Out](#close-out)

## Prepare

- [ ] Review the complete diff since the previous tag, including intended uncommitted changes.
- [ ] Confirm dependency minimums and their fixture pins agree; disclose dropped compatibility.
- [ ] Add a dated `## [MAJOR.MINOR.PATCH] - YYYY-MM-DD` changelog entry and retain `Unreleased`.
- [ ] Create the versioned record from the [release notes template] and index it in the
      [release archive]. Mark candidates planned until finalized.
- [ ] Preserve existing tag identities; backfill omitted history without claiming a failed tag
      has been repaired.

## Validate

- [ ] Run `make release-changelog RELEASE_VERSION=vMAJOR.MINOR.PATCH` for the intended version.
- [ ] Run `make docs-markdown` and `make check-release` from the candidate checkout.
- [ ] Use a fresh `PYTHON_DIST_DIR` when old artifacts would mix versions; never delete unrelated
      build output merely to pass a gate.
- [ ] Record the exact candidate commit, commands, results, and outstanding hosted checks.
- [ ] Revalidate after changes; a passing working tree is not proof about a different tagged tree.

The release gate builds both distributions, checks metadata, and tests those same artifacts in
clean environments. It may download dependencies but does not publish.

## Tag and Publish

- [ ] Obtain authorization before creating or pushing an annotated release tag on the reviewed
      commit reachable from the default branch.
- [ ] Confirm tag-triggered CD validation succeeds, including the wheel-version match.
- [ ] For optional GitHub publication, follow the manual opt-in and environment safeguards in the
      [release policy]. A tag push alone does not publish a GitHub Release.
- [ ] Do not assume PyPI publication is enabled; no current workflow configures it.

## Close Out

- [ ] Review release notes and artifact integrity evidence before claiming publication succeeded.
- [ ] Update the archive's status based on actual results, not merely a committed document.
- [ ] Synchronize maintained branches according to the configured repository review policy.
- [ ] Record follow-up work and use a new version for post-release corrections; never move tags.

[release notes template]: ../../.github/RELEASE-NOTES-TEMPLATE.md
[contributor checklist]: ../../CONTRIBUTING.md#release-preparation
[release policy]: ../../RELEASE-POLICY.md
[release archive]: ../releases/README.md
