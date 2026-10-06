<!--
RELEASE-NOTES-TEMPLATE.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Release notes template for public changes, compatibility, and validation evidence.

Responsibilities
- Record release scope, compatibility, support boundaries, and validation.
- Explain publication, rollback, and outstanding limitations.

Maintainer Notes
- Keep guidance language- and platform-neutral; retain relevant CLI contracts.
- Keep local references aligned with the repository documentation.
- Link shared release guidance and changelog highlights instead of duplicating them.
-->

# Release Notes Template

Use this template when preparing a versioned document for the [release notes archive] and reviewed
notes for any corresponding GitHub Release. The committed record preserves the candidate's detailed
scope and validation evidence; it does not establish tagging or publication. Reconcile the notes
with the [changelog] and [reading guide], keep the sections that apply, and add more focused
sections when needed. Release notes should explain released behavior without depending on private
operational evidence.

For a new record, use `# Popo vMAJOR.MINOR.PATCH` and an introduction identifying either the
verified UTC tag date or the planned candidate's preparation date. Point its changelog reference to
the matching dated section. Resolve reference destinations relative to `docs/releases/`, sort them
by destination, and remove unused definitions; the links below resolve from this template's
`.github/` location.

- [Highlights](#highlights)
- [Change Scope](#change-scope)
- [Compatibility and Configuration](#compatibility-and-configuration)
- [Support Boundary](#support-boundary)
- [Validation](#validation)
- [Deployment and Rollback](#deployment-and-rollback)
- [Known Limitations and Follow-Up](#known-limitations-and-follow-up)

## Highlights

Link to the dated changelog entry instead of copying its change list:

> See the [changelog] for this version's concise change list.

For an initial scaffold without a dated changelog entry, record its highlights here.

## Change Scope

- Describe the package, infrastructure, automation, dependencies, artifacts, or documentation
  affected.
- State important areas intentionally left unchanged, especially when that distinction informs
  compatibility or deployment risk.
- Link relevant pull requests, issues, architecture decisions, or public documentation by reference.

## Compatibility and Configuration

- Identify breaking behavior, deprecations, migrations, dependency constraints, or configuration
  changes.
- Give breaking changes and deprecations their own subheadings when present so they cannot be
  overlooked in a broader summary.
- Record any required maintainer or consumer action.
- For CLI changes, cover commands, flags, configuration, output, and exit codes.
- Write `No compatibility or configuration changes.` when none apply.

## Support Boundary

- Record release-specific changes to supported runtimes, services, regions, interfaces, or operating
  assumptions.
- Distinguish stable public behavior from internal implementation details when that affects future
  maintenance or compatibility.
- Write `No support-boundary changes.` when none apply.

## Validation

Start with a link to the shared interpretation rules:

> Interpret these results using the [evidence boundaries].

- List checks completed against the exact checkout or artifact tested, with dates and results.
- Identify the candidate tag without embedding a commit SHA, and link available artifact-integrity
  evidence.
- Include relevant automated tests, static checks, build results, artifact inspection, CLI output
  and exit-code checks, and representative manual verification.
- Record failures, skipped checks and reasons, and outstanding release-specific evidence.
- Describe historical preparation requirements in the past tense; preserve their recorded outcomes.
- Link shared rules instead of repeating generic validation or publication disclaimers.

## Deployment and Rollback

Link to the shared tagging and publication rules:

> Shared tagging and publication rules are in [release operations].

- Describe release-specific changes to deployment or publication behavior, if any.
- Describe expected package, infrastructure, dependency, artifact, or operational effects.
- State whether resource replacements, data migrations, DNS or publication changes, or service
  interruption are expected.
- Provide a safe rollback or forward-fix approach appropriate to the release.

## Known Limitations and Follow-Up

- Record intentional limitations, deferred work, and monitoring expectations.
- Link public follow-up issues when available.
- Write `None.` when no release-specific limitations or follow-up work remain.

Before committing the release document, remove unused guidance, verify links and version numbers,
and ensure credentials, private identifiers, and confidential evidence are absent.

[changelog]: ../CHANGELOG.md
[release notes archive]: ../docs/releases/README.md
[evidence boundaries]: ../docs/releases/README.md#evidence-boundaries
[reading guide]: ../docs/releases/README.md#reading-the-records
[release operations]: ../docs/releases/README.md#release-operations
