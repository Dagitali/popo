<!--
README.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Repository automation map and intentional portability boundaries.

Responsibilities
- Map the repository's automation and contributor-facing templates.
- Explain purposeful differences from the sibling reference project.
- Separate local validation from hosted enforcement and publication.

Maintainer Notes
- Update this map when workflows or contributor interfaces change.
- Distinguish local configuration from enabled hosted repository settings.
-->

# GitHub Configuration

- [Conventions](#conventions)
- [Intentional Differences](#intentional-differences)
- [Validation](#validation)

## Conventions

The shared conventions are adapted from the sibling `aws-cdk-static-site` repository. They describe
development of this Python CLI, not requirements imposed on repositories that the CLI checks.

| Surface | Responsibility |
| --- | --- |
| [PR gates](workflows/pr.yml) | Enforce optional JSON-configured target-branch routing without assuming GitFlow. |
| [CD](workflows/cd.yml) | Validate annotated release tags and optionally publish GitHub Releases under explicit gates. |
| [Disposable installation](workflows/deployment-test.yml) | Manually test built distributions across six OS/Python combinations without cloud deployment. |
| [CI](workflows/ci.yml) | Validate both Python versions, dependency boundaries, coverage, and Linux/macOS/Windows installations. |
| [SBOM](workflows/sbom.yml) | Inventory the isolated runtime environment in validated CycloneDX JSON; retain for 14 days. |
| [Security](workflows/security.yml) | Manually audit resolved runtime dependencies with pip-audit and retain findings for 14 days. |
| [Python setup](actions/setup-python-project/action.yml) | Cache Python, install extras, and run dependency-integrity diagnostics. |
| [Dependabot](dependabot.yml) | Weekly Actions, Python, and pre-commit update PRs against the default branch, scheduled in UTC. |
| [Issue chooser](ISSUE_TEMPLATE/config.yml) | Offer structured bug, feature, and documentation forms; retain blank issues. |
| [PR template](pull_request_template.md) | Record compatibility, validation, documentation, and delivery implications. |
| [Release categories](release.yml) | Categorize generated notes; does not publish releases. |
| [Release notes template](RELEASE-NOTES-TEMPLATE.md) | Capture release scope and validation evidence. |
| [Branch protection](BRANCH-PROTECTION.md) | Document proposed hosted safeguards without claiming they are enabled. |

## Intentional Differences

- No AWS deployment, synthesis, or `cdk-nag` workflow: these are consumer-specific.
- No imposed GitFlow gate: routing is opt-in through `PR_TARGET_RULES`.
- Release validation is automatic for version tags; publication is manual and disabled by default.
  See the [release policy](../RELEASE-POLICY.md) for activation and safeguards.
- SBOM generation calls CycloneDX directly, not a Dagitali lifecycle action. Its isolated target
  contains the installed project, runtime dependencies, and bootstrap tools, not development extras
  or the generator. It describes that resolved environment, not all supported dependency
  combinations or a released artifact.
- Security auditing replaces infrastructure analysis with known-vulnerability checks of resolved
  runtime dependencies. It excludes the unpublished project itself and pip, never applies fixes, and
  sends dependency names/versions to PyPI's advisory service. It is manual and advisory for branch
  protection, but findings still fail its run.
- No Sphinx or synthesis jobs: popo has neither Sphinx sources nor CDK examples.
- Branch coverage is reported without importing the construct library's coverage threshold.
- No copied funding accounts or named code owners: sponsorship and review authority must be selected
  for this project.
- No links to missing support or security policies. Blank issues remain available; suspected
  vulnerabilities must not be disclosed publicly. A private reporting channel still needs maintainer
  configuration.

## Validation

Run `make check`, validate workflow syntax with `actionlint`, and review YAML structure after
automation changes. CI preserves full-SHA action pins, read-only job permissions, and both
wheel/source clean-install tests. No hosted settings are changed by local edits.

SBOM runs on relevant pushes to `main` and manual dispatch. Security runs only on manual dispatch.
Neither is suitable as a required PR check. Tool versions are pinned in workflow environment
variables and require deliberate maintenance; their transitive dependencies are not locked. No
credentials, package publication, or AWS operations are involved.

CD and disposable installation tests are also not required PR checks. Only CD's explicitly enabled
publication job has write permissions; the other jobs remain read-only.
