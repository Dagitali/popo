<!--
LEARNINGS.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Reusable failure patterns, causes, repairs, and verification paths.

Maintainer Notes
- Keep claims grounded in repository sources and preserve consumer-owned policy.
- Link to detailed guidance rather than maintaining competing copies.
-->
# Learnings

These lessons follow implementation, tests, and recorded release history. Each uses **Symptom →
Cause → Fix → Verification**. The [incident runbook] owns detailed recovery procedures.

- [Default Tests Omit Artifact Layers](#default-tests-omit-artifact-layers)
- [Minimum Dependencies Drift](#minimum-dependencies-drift)
- [A Passing Markdown Check Misses a Reference](#a-passing-markdown-check-misses-a-reference)
- [A Tagged Release Lacks Its Changelog Entry](#a-tagged-release-lacks-its-changelog-entry)
- [Documentation Copies the Wrong Project Policy](#documentation-copies-the-wrong-project-policy)

## Default Tests Omit Artifact Layers

**Symptom:** Source tests pass while the installed package fails.

**Cause:** Default discovery includes unit and integration tests; it does not build artifacts.

**Fix:** Select `make test-distribution test-installation` for packaging changes, or
`make check-release` when validating the same built artifacts for a candidate.

**Verification:** Confirm both the wheel and source distribution pass their contents and
clean-install checks. Follow the [test layout]; prebuilt artifacts do not exercise build-on-demand.

## Minimum Dependencies Drift

**Symptom:** A dependency update causes `make dependency-policy` to fail.

**Cause:** A minimum-version pin differs from the declared lower bound in package metadata.

**Fix:** Reconcile the intended support range and its fixture together. Do not weaken the check.

**Verification:** Run the policy check and the lowest-dependency tests described in the
[contributing guide].

## A Passing Markdown Check Misses a Reference

**Symptom:** A label renders as plain text or an external badge does not show the expected result.

**Cause:** Local validation checks destinations and supported anchors, not undefined labels, inline
image links, external availability, or the meaning of remote content.

**Fix:** Review reference definitions and image targets separately; inspect remote results when
needed. For badges, check whether branch/event filters match the workflow.

**Verification:** Run `make docs-markdown` and separately inspect rendered references and external
destinations. See the [configuration reference] for the checker's exact scope.

## A Tagged Release Lacks Its Changelog Entry

**Symptom:** CD rejects a tag even though a later checkout contains the release entry.

**Cause:** Validation reads the tagged tree. The [0.1.3 record] documents this failure and its
subsequent historical correction.

**Fix:** Preserve the tag and record corrections in a later version with its own dated entry.

**Verification:** Validate the intended candidate through the [release playbook]; a later passing
checkout does not repair the original tag.

## Documentation Copies the Wrong Project Policy

**Symptom:** Guidance names nonexistent commands or implies deployment, support, or publishing
behavior that this repository does not provide.

**Cause:** Shared structure was copied together with project-specific assumptions.

**Fix:** Trace commands to Make, policy to package configuration, and automation to workflow YAML.
Generalize reusable guidance while retaining purposeful domain differences.

**Verification:** Follow the [documentation synchronization guide], validate links, and review
claims separately from syntax. Do not change implementation merely to make copied prose true.

[documentation synchronization guide]: CONTRIBUTING.md#documentation-synchronization
[contributing guide]: CONTRIBUTING.md#github-automation
[configuration reference]: docs/CONFIGURATION.md
[release playbook]: docs/playbooks/release.md
[0.1.3 record]: docs/releases/v0.1.3.md
[incident runbook]: docs/runbooks/incident-response.md
[test layout]: tests/README.md
