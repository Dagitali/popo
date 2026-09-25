<!--
update-required-checks.md
popo/docs/runbooks

Copyright © 2026 Dagitali LLC. All rights reserved.

Safe transition, diagnosis, and verification of required repository checks.

Maintainer Notes
- Keep the protection policy authoritative; do not infer active hosted settings.
- Require explicit authorization for workflow dispatches and hosted-rule changes.
-->

# Update Required Checks

Use this runbook when a job name, matrix, event trigger, or protected-branch policy changes. The
[branch protection policy] defines the proposed baseline; this procedure helps an authorized
maintainer transition and verify it. It does not establish that hosted controls are enabled.

- [Prerequisites and Boundaries](#prerequisites-and-boundaries)
- [Plan the Transition](#plan-the-transition)
- [Observe and Update](#observe-and-update)
- [Verify Enforcement](#verify-enforcement)
- [Diagnose Missing Results](#diagnose-missing-results)
- [Recover and Record](#recover-and-record)

## Prerequisites and Boundaries

Identify the affected branches, approved operator, representative pull request, and existing
required-check selection. Record current rules and bypass actors in an appropriate private operator
record before any authorized edit. Do not put tokens or private screenshots in public docs.

Preserve review, conversation-resolution, force-push, deletion, and bypass protections. Select only
checks that report for every applicable pull request and, if used, merge group. Manual installation,
security, release-publication, and post-push jobs are not universal PR gates. Follow the policy's
[check selection principles] rather than making every available job required.

Popo does not require a `develop` branch or GitFlow routing by default. Do not import a fixed branch
sequence from another project. Documentation edits and local checks do not authorize hosted edits,
workflow dispatches, test pull requests, or bypass changes.

## Plan the Transition

1. Compare the proposed change with the [CI workflow], [PR gates], and current hosted selection.
2. Inspect event coverage, path filters, job conditions, matrix exclusions, dependencies, and
   concurrency cancellation for cases where a required result may never appear.
3. Preserve unique job names. A step rename is not a required-job rename; inspect the emitted job
   result rather than selecting an internal step label.
4. For a renamed required result, plan an overlap: retain the old result while introducing and
   validating its replacement. Coordinate workflow integration with the authorized rules change.
5. Use `make github-actions-pins python-policy` and relevant workflow tests for workflow edits;
   follow with `make check`. These validate repository contracts, not hosted enforcement.

The current CI matrix covers supported Python versions, dependency boundaries, and cross-platform
installation. Read current YAML instead of copying matrix-expanded names from this runbook.

## Observe and Update

With the necessary authorization, obtain representative successful hosted results for the affected
branch and event. Record exact emitted check names and their source, including matrix expansion. For
merge queues, also verify merge-group results. Do not infer these solely from YAML.

Add verified replacements to the intended hosted rule while retaining old requirements during the
overlap. Preserve unrelated protections. Remove obsolete requirements and compatibility jobs only
after their replacements enforce the intended gate. If overlap is impractical, agree on a narrow
coordinated transition and recovery plan before proceeding; do not normalize a broad bypass.

## Verify Enforcement

For an authorized representative PR, verify that:

- Every intended required result is reported and must pass;
- A deliberately failing required result blocks merging;
- Advisory results have not accidentally become required;
- No obsolete result remains permanently expected or pending;
- Review and history protections remain intact; and
- Merge groups receive the required results when a queue is enabled.

Use a disposable test change for failure verification, not a broken protected-branch commit. Record
what was actually observed. Passing local tests or a successful hosted workflow alone is not proof
that the rules enforce the intended policy.

## Diagnose Missing Results

Compare the required name and expected source with the latest representative result. Check the
target branch and event, filters, conditions, matrix exclusions, skipped dependencies, and canceled
runs. Look for duplicate job names or a stale name left behind by a rename. For queues, confirm
`merge_group` coverage in every required workflow.

The PR gate validates optional `PR_TARGET_RULES`; an unset variable means no routing restrictions.
Do not misdiagnose a configured routing failure as a missing CI result or replace the rule merely to
make a PR pass. Consult [configurable routing] and the [incident runbook] for policy diagnosis.

## Recover and Record

If the transition blocks valid changes or weakens enforcement, coordinate restoration of the last
known-good required-check set and compatible workflow results. Restoring names alone is insufficient
if the workflow no longer emits them. Preserve history and review protections during recovery and
verify the restored configuration before retrying the transition.

Update affected protection guidance and contributor documentation through normal review. Record the
tested revision, representative results, authorized settings changes, and outstanding verification
in the appropriate operator record. Keep private operational evidence out of the repository.

[branch protection policy]: ../../.github/BRANCH-PROTECTION.md
[configurable routing]: ../../.github/BRANCH-PROTECTION.md#configurable-pr-routing
[check selection principles]: ../../.github/BRANCH-PROTECTION.md#selection-principles
[CI workflow]: ../../.github/workflows/ci.yml
[PR gates]: ../../.github/workflows/pr.yml
[incident runbook]: incident-response.md
