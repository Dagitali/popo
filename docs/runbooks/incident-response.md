<!--
incident-response.md
popo/docs/runbooks

Copyright © 2026 Dagitali LLC. All rights reserved.

Bounded diagnosis and recovery for repository, dependency, and release failures.

Maintainer Notes
- Preserve immutable tags and distinguish local changes from hosted state.
- Keep credentials and private evidence out of public reports.
-->

# Repository Incident Response

This runbook covers repository checks, CI, package artifacts, and release validation. It does not
authorize changing hosted settings, rerunning workflows, publishing, accessing secrets, or mutating
consumer repositories. Obtain the appropriate maintainer authorization for external operations.

- [Triage](#triage)
- [Contain and Recover](#contain-and-recover)
  - [Dependency Minimum Mismatch](#dependency-minimum-mismatch)
  - [Test and Configuration Mismatch](#test-and-configuration-mismatch)
  - [Missing Dated Changelog](#missing-dated-changelog)
  - [Local Environment or Artifact Failure](#local-environment-or-artifact-failure)
  - [Publication or Hosted-Protection Failure](#publication-or-hosted-protection-failure)
- [Verify and Close](#verify-and-close)

## Triage

1. Identify the workflow, job, step, exact commit or tag, and first meaningful error. A failed
   `make` target is often the consequence, not the cause.
2. Inspect `git status --short` and record the checked-out revision before reproducing locally.
   Current branch contents may differ from the failed hosted checkout.
3. Classify the failure as repository policy, test/configuration mismatch, environment, artifact, or
   publication. Preserve relevant evidence without copying sensitive data into tracked files.
4. Stop further release operations when artifact identity or publication integrity is uncertain.
   Preserve tags and evidence rather than rewriting history to make an old run pass.
5. Keep suspected credential exposure or vulnerability details out of public issues and coordinate
   privately with maintainers before recovery operations.

## Contain and Recover

### Dependency Minimum Mismatch

If `make dependency-policy` reports different expected and received versions, compare the declared
lower bound in `pyproject.toml` with `requirements/lowest.txt`. This checks file contents, not the
installed version. When accepting a newer minimum, update both in the same change and document the
compatibility impact. Otherwise retain the intended supported minimum. Follow the [dependency update
policy]; do not weaken validation merely to merge a Dependabot proposal.

### Test and Configuration Mismatch

A `KeyError` in a repository-contract test can mean the test assumes a configuration key that no
longer exists. Confirm the intended policy before restoring configuration or removing the test.
Update related contributor and release guidance together, retain tests for the actual contract, and
rerun the quality gate. Avoid adding a default value just to conceal an incorrect expectation.

### Missing Dated Changelog

The [CD workflow] checks out the selected tag before running release validation. Verify that exact
tree contains `## [MAJOR.MINOR.PATCH] - YYYY-MM-DD` with a valid date for the selected version. Run
`make release-changelog RELEASE_VERSION=vMAJOR.MINOR.PATCH` in the intended candidate checkout.

If the existing tag lacks its entry, adding it to a later branch will not fix a rerun against that
tag. Backfill history transparently and prepare a new version containing its own dated entry. Do not
move the original tag. Follow the [release playbook] for the corrected candidate.

### Local Environment or Artifact Failure

Use `make show-venv` to inspect environment selection and review the [development setup]. Do not
replace an existing environment or install packages into an unrelated interpreter without deciding
that scope explicitly. Use [focused tests] to separate source-import failures from clean installed
package failures.

If artifact tests find mixed versions, use a fresh build directory through `PYTHON_DIST_DIR` rather
than deleting broad directories. Verify the wheel and sdist built from the same candidate; do not
silently replace published artifacts or reuse a released version.

### Publication or Hosted-Protection Failure

Use the [release policy] to distinguish validation from optional publication. A passing tag build
does not prove that a GitHub Release exists, and a workflow file does not prove environment
reviewers or branch rules are configured. Review the exact run and artifact evidence before any
authorized retry or settings change. There is no cloud deployment to clean up in Popo's workflows.

## Verify and Close

Run the focused reproduction, then `make check` and any relevant artifact checks. Confirm hosted
results separately when applicable; local success does not repair a historical failed run. Record
the cause, impact, correction, verification, and outstanding work. Add regression coverage where it
protects intended behavior, and update this runbook when a reusable recovery procedure changes. Do
not claim completion while a required check remains failing or unverified.

[CD workflow]: ../../.github/workflows/cd.yml
[development setup]: ../../CONTRIBUTING.md#development-setup
[dependency update policy]: ../../CONTRIBUTING.md#github-automation
[release policy]: ../../RELEASE-POLICY.md
[focused tests]: ../TESTING.md
[release playbook]: ../playbooks/release.md
