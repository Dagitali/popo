<!--
RELEASE-POLICY.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Release validation, artifact integrity, and optional publication safeguards.

Maintainer Notes
- Describe configured automation without claiming hosted protections are enabled.
- Keep local links and documented behavior consistent with repository sources.
-->

# Release Policy

`popo` separates validation from publication. No workflow publishes to PyPI or deploys cloud
resources. Package versions come from Git tags through `setuptools-scm`.

- [Scope](#scope)
- [Versioning and Compatibility](#versioning-and-compatibility)
  - [Release Classification](#release-classification)
  - [Deprecation and Support](#deprecation-and-support)
- [Candidate Validation](#candidate-validation)
- [Release Artifacts](#release-artifacts)
- [Release Notes](#release-notes)
- [Opt-in GitHub Publication](#opt-in-github-publication)
- [Disposable Installation Test](#disposable-installation-test)

## Scope

This public policy describes the configured validation and publication boundaries. It excludes
credentials, private recovery procedures, and account-specific controls. Documented gates do not
establish that hosted environment protections or repository settings have been enabled.

## Versioning and Compatibility

The [changelog] follows Semantic Versioning and records public changes. Package versions come from
Git metadata; a source-import fallback or a development build is not evidence of a release. Preserve
annotated tag identities rather than moving a tag to repair a later-discovered defect.

Popo is alpha/pre-1.0. Review commands, flags, configuration defaults, accepted inputs, diagnostics,
and exit codes when assessing compatibility. A stricter validator can require consumer migration
even if its command name is unchanged. Identify breaking changes and migration steps in the
versioned notes; distinguish backward-compatible maintenance from public-contract changes.

### Release Classification

Assess the complete change set, including behavior affected by stricter validation:

| Change | Versioning consideration |
| --- | --- |
| Compatible bug fix, documentation repair, or packaging correction | Patch candidate |
| New command, optional setting, or other user-facing capability | Minor candidate |
| Required migration or intentionally incompatible public behavior | Explicit compatibility review and release notes; after 1.0, a major release |

During pre-1.0 development, a minor release can refine the public interface. Do not assume every
dependency update is patch-safe: dropped runtime support or changed accepted inputs can affect
consumers. Classify by the resulting behavior, not the number of changed files.

### Deprecation and Support

No fixed deprecation window or stable-line backport commitment is currently documented. Establish
those commitments explicitly before advertising stable support. Consult the [support guide] for the
current boundary and the [roadmap] for readiness considerations.

## Candidate Validation

The [CD workflow] validates pushed `v*.*.*` tags or a manually selected existing tag. A valid
release tag is annotated, uses `vMAJOR.MINOR.PATCH`, and points to a commit reachable from the
repository's default branch. Tags must not be moved. The tagged checkout must contain the current
packaging, tests, and setup action; older incompatible tags fail validation rather than bypassing
it.

Validation requires a dated [changelog] entry, `make check`, both built distributions, `twine check`,
clean-install tests, and a wheel version matching the tag.

## Release Artifacts

The workflow builds the wheel and source distribution once and tests those same artifacts in clean
environments. It also generates a validated runtime SBOM and SHA-256 checksums. Downloads remain
available as workflow artifacts for 14 days.

## Release Notes

Use the [release notes template] to describe public changes, compatibility, and completed
validation. For this CLI, compatibility includes commands, flags, configuration, output, and exit
codes. Identify breaking changes and required consumer actions rather than assuming that a passing
build establishes compatibility. Keep notes consistent with the [changelog] and tested artifacts.

Maintain release-aligned records in the [release archive]. Mark untagged candidates as planned and
record validation against the exact candidate, not another checkout. CD currently generates GitHub
Release notes rather than reading these records automatically; review published notes for
consistency with the maintained record.

## Opt-in GitHub Publication

Publication is disabled by default. To enable it, a maintainer must:

1. Configure the `release` GitHub environment with required reviewers and appropriate branch
   restrictions. Merely referencing an environment does not configure protection.
2. Set the repository variable `ENABLE_RELEASE_PUBLISHING` to exactly `true`.
3. Manually run CD **from the default branch**, select an existing release tag, and explicitly
   select `publish`.
4. Review and approve the environment job when prompted.

The publication job receives only the validated artifacts. It does not check out or run tagged
project code. It checks the remote tag object has not changed and verifies artifact checksums before
creating the GitHub Release. Existing releases are not overwritten; historical releases are not
automatically marked latest. The token is scoped to that job.

Environment protection depends on repository configuration and GitHub plan capabilities. Do not
enable publication without the intended protections. These local files do not configure reviewers,
repository variables, branch protection, or PyPI credentials.

## Disposable Installation Test

[deployment-test.yml] is the package-oriented equivalent of a disposable deployment test. Run it
manually against the selected workflow ref to build and install its wheel and sdist in clean
environments on Linux, macOS, and Windows with Python 3.13 and 3.14. It tests CLI help, version,
successful checks, and failing checks outside the checkout. Hosted runners dispose of the temporary
environments. It does not test a published package, mutate a consumer repository, or deploy external
resources.

[release notes template]: .github/RELEASE-NOTES-TEMPLATE.md
[CD workflow]: .github/workflows/cd.yml
[deployment-test.yml]: .github/workflows/deployment-test.yml
[changelog]: CHANGELOG.md
[roadmap]: ROADMAP.md
[support guide]: SUPPORT.md
[release archive]: docs/releases/README.md
