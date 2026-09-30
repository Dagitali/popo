<!--
SUPPORT.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Help channels, supported interfaces, and maintenance expectations.

Maintainer Notes
- Keep claims grounded in repository sources and preserve consumer-owned policy.
- Link to detailed guidance rather than maintaining competing copies.
-->

# Support

- [Support Boundary](#support-boundary)
- [Where to Get Help](#where-to-get-help)
- [What to Include](#what-to-include)
- [Maintenance Expectations](#maintenance-expectations)

## Support Boundary

Popo's consumer interface is the documented CLI and configuration. The package root intentionally
exports only `__version__`; internal checker modules are not a stable consumer API. Consult the
[configuration reference] for supported input formats and limitations.

`pyproject.toml` declares supported Python versions and dependency ranges; CI supplies validation
evidence. A passing local check does not establish compatibility with every platform or consumer
policy. Review the [release archive] for version-specific changes.

## Where to Get Help

- Start with the [README], [documentation index], and [learnings].
- Use the [issue forms] for reproducible bugs, concrete feature requests, or documentation fixes.
- Follow the [security policy] for suspected vulnerabilities.
- Follow the [Code of Conduct] for participation and conduct concerns.

Public reports must omit credentials, private repository content, personal information, and
confidential incident evidence. Request a private channel for sensitive material.

## What to Include

Provide the Popo version or revision, interpreter and operating system, exact command, expected and
observed results, and a minimal sanitized example. Identify whether the failure occurs in a source
checkout or an installed wheel/source distribution. Include relevant configuration and diagnostics,
but inspect them for sensitive paths and values first.

## Maintenance Expectations

The package is alpha/pre-1.0. Review compatibility changes before updating a consumer's pinned
revision. Documentation does not promise a response deadline, backport window, or stable-release
support period; those commitments require an explicit maintainer decision.

The [release policy] distinguishes candidate validation, tagging, and optional publication. Consumer
CI, deployment, remediation, and hosted settings remain consumer responsibilities.

[issue forms]: .github/ISSUE_TEMPLATE/
[Code of Conduct]: CODE_OF_CONDUCT.md
[learnings]: LEARNINGS.md
[README]: README.md
[release policy]: RELEASE-POLICY.md
[security policy]: SECURITY.md
[configuration reference]: docs/CONFIGURATION.md
[documentation index]: docs/README.md
[release archive]: docs/releases/README.md
