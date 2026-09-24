<!--
BRANCH-PROTECTION.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Branch-protection guidance for reviewed, validated changes.

Responsibilities
- Define reusable review, validation, and direct-update safeguards.
- Identify repository-specific check candidates and optional routing policy.
- Describe safe required-check transitions without changing hosted settings.

Maintainer Notes
- This is a proposed baseline, not evidence of active hosted settings.
- Verify emitted check names before configuring required checks.
-->

# Branch Protection

Apply this baseline to the repository's integration and release branches as appropriate. No GitFlow
branch names or source-branch prefixes are required by default. CI runs for all pull requests,
pushes to `main`, merge groups, and manual dispatches.

- [Purpose](#purpose)
- [Branch Roles](#branch-roles)
- [Shared Protection Baseline](#shared-protection-baseline)
- [Required Checks](#required-checks)
  - [Selection Principles](#selection-principles)
  - [Repository-Specific Checks](#repository-specific-checks)
- [Configurable PR Routing](#configurable-pr-routing)
- [Disallowing Direct Updates](#disallowing-direct-updates)
- [Merge Queue](#merge-queue)
- [Updating Required Checks](#updating-required-checks)
- [Maintenance Notes](#maintenance-notes)

## Purpose

Protected branches should enforce review and successful validation at the hosted repository
boundary. Local hooks provide earlier feedback but cannot replace server-side enforcement. CI that
runs after a direct push cannot retroactively prevent that push.

Prefer repository rulesets when available, or equivalent branch protection rules. If the
repository's visibility or plan does not support these controls, treat this document as a target
configuration, not an active safeguard. Retain the pull-request workflow voluntarily and reassess
enforcement when repository capabilities change.

## Branch Roles

The protection principles apply regardless of language, build system, or branching model. Choose
integration and release branches appropriate to the project; no separate `develop` branch or fixed
source-branch prefix is required. Apply the shared baseline to each protected branch and use
[configurable PR routing] only when needed.

The [release workflow] requires annotated release tags to point to commits reachable from the
repository's default branch. CI's post-push trigger currently names `main`; changing the default or
integration branches requires reviewing workflow triggers as well as hosted protections.
Pull-request and merge-group validation are not restricted to `main`.

Release pull requests should summarize validation evidence, compatibility impact, artifact effects,
and rollback considerations. If maintaining multiple release lines, identify the affected line and
plan how fixes reach the other maintained branches through reviewed pull requests. Local merge or
branch-finishing commands are not substitutes for hosted review.

Tag validation and optional release publication are post-merge safeguards, not replacements for
required pull-request checks. See the [release policy].

## Shared Protection Baseline

- Require pull requests and resolution of review conversations.
- Require independent approval where reviewer availability permits it.
- Block force pushes and branch deletion; keep bypass access narrowly scoped.
- Require checks that run on every pull request to the protected branch.
- Treat local hooks as feedback, not a substitute for server-side protection.

Dismiss stale approvals after review-relevant changes when independent review is required. Require
Code Owner review only when a maintained `CODEOWNERS` file and an eligible reviewer exist. For solo
maintenance, use zero mandatory approvals or document a narrow bypass policy: authors cannot provide
independent approval of their own changes.

Consider up-to-date branches, approval of the latest reviewable push, linear history, signed
commits, and merge queue according to project needs. Confirm contributor, bot, and merge-method
compatibility before requiring optional controls.

## Required Checks

### Selection Principles

- Require only checks that run for every pull request to the protected branch.
- Keep job names unique across workflows; step names are not required-check names.
- Select exact names from successful hosted runs, including expanded matrix names.
- Avoid requiring path-filtered workflows unless an alternative reports the required result for
  excluded changes.
- Choose strict checks when branches must be current with their target before merging; use loose
  checks only when the integration risk is acceptable.
- Ensure every required workflow also handles `merge_group` before enabling merge queue.

### Repository-Specific Checks

The `Continuous Integration (CI)` workflow has a `check` job for Python 3.13 and 3.14. Both matrix
entries run lint, typing, tests, repository checks, artifact validation, and clean installations.
Select the exact check names from a successful hosted run rather than guessing their rendered names.
Preserve existing required-check names when editing the matrix or jobs.

Additional CI candidates are the four Python/dependency-boundary combinations and the macOS/Windows
clean-install jobs. These run for all PRs and merge groups. Select their emitted names only after
successful hosted runs. SBOM and manual security checks are supplementary and must not be required
for pull requests.

Merge-group events run the same validation, but no merge queue or branch ruleset is enabled by
committing these files. Confirm hosted settings separately. Package publication and deployment are
not CI prerequisites. Optional GitHub release publication is governed by the [release policy].

## Configurable PR Routing

The `Pull Request (PR) Gates` workflow validates the repository variable `PR_TARGET_RULES`. Unset
means `{}`: no target-branch restrictions. To adopt GitFlow-like routing for `main`, for example,
set the variable to:

```json
{"main": {"head_pattern": "(release|hotfix)/.+", "same_repository": true}}
```

Keys are exact target branches. `head_pattern` is a Python regular expression matched against the
entire source branch and is required for each configured target. `same_repository` is an optional
boolean, defaulting to false. Unknown fields or invalid configuration fail the gate. Targets not
listed are unrestricted. Fork PRs must satisfy the same source-branch pattern and are rejected when
their target's rule sets `same_repository` to true.

Merge groups validate configuration but inherit routing checks from queued PRs. Require `Guard pull
request target` on the affected branches before relying on this enforcement; when rules change,
rerun checks for queued PRs before merging. Repository variables and branch protections are not
created by committing the workflow.

## Disallowing Direct Updates

Configure an active ruleset or equivalent branch protection for each integration or release branch.
Require pull requests, successful required checks, conversation resolution, and the chosen review
policy. Block force pushes and deletion. Include administrators in enforcement where practical and
document any recovery exceptions. Review overlapping rules and bypass actors before claiming direct
updates are blocked.

These are maintainer configuration steps, not changes made by these files. Verify hosted enforcement
separately; workflow success alone does not prove it is enabled.

## Merge Queue

Both `ci.yml` and `pr.yml` handle `merge_group`. Before enabling a queue, verify that each selected
required check reports for both pull requests and queued merge groups. Any newly required workflow
must preserve this coverage. Manual deployment tests, release publication, security audits, and
post-push SBOM runs are not queue prerequisites.

## Updating Required Checks

1. Add the replacement job or matrix entry without removing the existing required result.
2. Obtain successful hosted runs and record the exact emitted check names.
3. Update the hosted required-check selection in a coordinated transition.
4. Verify on a representative pull request that a failing required result blocks merging and, if
   enabled, that merge groups receive the same checks.
5. Remove obsolete jobs only after their verified replacements enforce the intended gate.

If the transition leaves a required result pending or absent, restore the previous working workflow
and required-check selection while investigating. Do not bypass validation merely to complete the
transition.

## Maintenance Notes

- Keep this guidance aligned with the [CI workflow], [PR gates], [release policy], [contributing
  guidelines], and actual hosted settings.
- Revisit check selections when job names, matrices, triggers, or protected branches change.
- Keep branch roles and routing rules aligned without imposing one branching model.
- Treat language, platform, and tool versions as implementation details, not permanent policy.
- Review bypass access periodically and verify protection after material changes.

[Branch Roles]: #branch-roles
[Configurable PR Routing]: #configurable-pr-routing
[Disallowing Direct Updates]: #disallowing-direct-updates
[Maintenance Notes]: #maintenance-notes
[Merge Queue]: #merge-queue
[Purpose]: #purpose
[Repository-Specific Checks]: #repository-specific-checks
[Required Checks]: #required-checks
[Selection Principles]: #selection-principles
[Shared Protection Baseline]: #shared-protection-baseline
[Updating Required Checks]: #updating-required-checks
[contributing guidelines]: ../CONTRIBUTING.md
[release policy]: ../RELEASE-POLICY.md
[release workflow]: workflows/cd.yml
[CI workflow]: workflows/ci.yml
[PR gates]: workflows/pr.yml
