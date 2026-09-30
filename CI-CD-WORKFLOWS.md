<!--
CI-CD-WORKFLOWS.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Workflow roles, triggers, validation layers, and publication boundaries.

Maintainer Notes
- Keep claims grounded in repository sources and preserve consumer-owned policy.
- Link to detailed guidance rather than maintaining competing copies.
-->

# CI/CD Workflow Map

Workflow YAML is authoritative. This map explains responsibilities without claiming that hosted
branch rules, environment reviewers, or publication settings are enabled.

- [Workflow Overview](#workflow-overview)
- [PR Gates and CI](#pr-gates-and-ci)
- [Security and Inventory](#security-and-inventory)
- [Disposable Installation Test](#disposable-installation-test)
- [Release Validation and Publication](#release-validation-and-publication)
- [Required Checks and Local Validation](#required-checks-and-local-validation)

## Workflow Overview

| Workflow | Trigger | Responsibility |
| --- | --- | --- |
| [PR gates] | Pull requests and merge groups | Validate optional branch-routing policy |
| [CI] | Pull requests, pushes to `main`, merge groups, manual dispatch | Source, dependency-boundary, distribution, and installation validation |
| [Security] | Manual dispatch | Audit resolved runtime dependencies |
| [SBOM] | Relevant pushes to `main`, manual dispatch | Generate a validated dependency inventory |
| [Installation] | Manual dispatch | Exercise disposable installations across platforms |
| [CD] | `v*.*.*` tag pushes, manual dispatch selecting an existing tag | Validate tagged artifacts; publish only with explicit opt-in |

CI, CD, security, SBOM, and installation jobs reuse the [Python setup action]. PR routing checks use
event metadata without a checkout or token permissions. Remote actions are pinned to full commit
SHAs, and jobs declare their required token permissions.

## PR Gates and CI

PR gates validate `PR_TARGET_RULES`; an unset value imposes no routing restrictions. Popo does not
require GitFlow branch names. Merge groups validate configuration and rely on queued PRs for routing
checks. The [branch-protection guide] defines the complete policy.

CI runs the default quality gate and artifact checks on Python 3.13 and 3.14, exercises both
lowest/newest dependency boundaries, reports coverage, and tests installations on macOS and Windows.
CI may download dependencies; it does not deploy resources or publish packages. Local validation
does not establish hosted platform success.

## Security and Inventory

The manual security job installs runtime dependencies and an isolated auditor, then runs `pip-audit`
without automatic fixes. Advisory queries disclose dependency names and versions to the service used
by the tool. Findings are uploaded when available, including after a failed audit.

The SBOM job inventories the installed project, runtime dependencies, and bootstrap tools while
keeping development extras and the generator separate. It validates CycloneDX output and retains it
as a short-lived workflow artifact. An inventory is not proof that dependencies are safe.

## Disposable Installation Test

The manual installation workflow builds and tests the selected checkout on Linux, macOS, and Windows
with Python 3.13 and 3.14. It creates temporary environments and exercises the installed CLI outside
the source tree. Despite its `deployment-test.yml` filename, it performs no cloud deployment and
does not test an already-published package.

## Release Validation and Publication

CD verifies an existing annotated release tag, its reachability from the default branch, a matching
dated changelog entry, and the built wheel version. It validates source, builds both distributions,
tests those artifacts, and produces checksums and an SBOM.

A tag push validates artifacts but does not publish a GitHub Release. Publication requires manual
dispatch from the default branch, an explicit `publish` selection, the enabling repository variable,
and the release environment. See the [release policy] for the complete safeguards. No workflow
publishes to PyPI or creates release tags.

## Required Checks and Local Validation

Select required check names from observed hosted results according to the [branch-protection guide].
Manual security/installation jobs and post-push or release jobs are not universal PR gates. Use the
[required-check runbook] when coordinating renamed results and hosted rules.

Run `make check` for the default source gate, `make docs-markdown` for local Markdown links, and
artifact targets from the [testing guide] when needed. Hosted checks remain distinct from these
local results.

[branch-protection guide]: .github/BRANCH-PROTECTION.md
[Python setup action]: .github/actions/setup-python-project/action.yml
[CD]: .github/workflows/cd.yml
[CI]: .github/workflows/ci.yml
[Installation]: .github/workflows/deployment-test.yml
[PR gates]: .github/workflows/pr.yml
[SBOM]: .github/workflows/sbom.yml
[Security]: .github/workflows/security.yml
[release policy]: RELEASE-POLICY.md
[testing guide]: docs/TESTING.md
[required-check runbook]: docs/runbooks/update-required-checks.md
