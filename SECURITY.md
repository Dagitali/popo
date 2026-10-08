<!--
SECURITY.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Private reporting guidance and the limits of read-only validation.

Maintainer Notes
- Keep claims grounded in repository sources and preserve consumer-owned policy.
- Link to detailed guidance rather than maintaining competing copies.
-->

# Security Policy

- [Reporting a Vulnerability](#reporting-a-vulnerability)
- [What to Include](#what-to-include)
- [Security Model](#security-model)
- [Consumer Responsibilities](#consumer-responsibilities)
- [Maintenance and Disclosure](#maintenance-and-disclosure)

## Reporting a Vulnerability

Do not publish exploit details, credentials, personal data, private repository contents, or
confidential incident evidence in an issue or pull request. Coordinate privately with maintainers.

Use GitHub private vulnerability reporting when it is enabled for this repository. If no private
channel is available, ask a maintainer for one without disclosing the vulnerability itself. This
document does not establish that a hosted reporting feature is enabled or that a particular email
address is monitored.

## What to Include

Provide the affected version or revision, impact, minimal sanitized reproduction, relevant
configuration, and any mitigation. Explain the execution environment and which files the checker was
permitted to read. Share only the sensitive evidence necessary through the agreed private channel.

## Security Model

Popo checks repository files without repairing them, executing referenced workflows, or fetching
remote code. The [architecture] explains the ownership boundaries. Read-only behavior does not
provide a general filesystem or process sandbox: run inspections with permissions appropriate to the
input repository.

Markdown destinations are constrained to the inspected root, and automation resolves local targets
within that root. These are specific validation rules, not guarantees for all filesystem access.
Format validation and full-SHA action pinning do not establish that referenced code is safe.

Repository automation pins remote actions and uses job-scoped permissions. Optional dependency
auditing and SBOM generation provide additional evidence; neither is a security certification. See
the [workflow map] for their network and execution boundaries.

## Consumer Responsibilities

Consumers own repository trust, execution isolation, dependency installation, configuration values,
diagnostic disclosure, and remediation. Avoid exposing secrets through inspected files or logs.
Retain checks for unsupported syntax and runtime behavior; static inspection does not replace hosted
workflow tests or an application security review.

## Maintenance and Disclosure

Report the affected release and any known mitigation so maintainers can assess the scope. Coordinate
publication of sensitive findings with maintainers. No response deadline, backport period, or
supported-security-release matrix is established by this document. See the [support guide] for the
current support boundary and the [release policy] for delivery safeguards.

[architecture]: ARCHITECTURE.md
[workflow map]: CI-CD-WORKFLOWS.md
[release policy]: CONTRIBUTING.md#release-policy
[support guide]: SUPPORT.md
