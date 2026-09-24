<!--
task-templates.md
popo/docs/development

Copyright © 2026 Dagitali LLC. All rights reserved.

Assistant-independent task briefs for bounded repository work.

Maintainer Notes
- Keep review-only requests distinct from implementation authorization.
- Select actual local checks rather than inventing tooling or hosted guarantees.
-->

# Repository Task Templates

Copy a template, replace bracketed fields, and remove irrelevant lines. Follow the [agent workflow]
and [agent instructions]; each task should produce one coherent, reviewable result.

- [Implement or Refactor](#implement-or-refactor)
- [Architecture or Interface Review](#architecture-or-interface-review)
- [Documentation Synchronization](#documentation-synchronization)
- [CI/CD Maintenance](#cicd-maintenance)
- [Incident Diagnosis](#incident-diagnosis)

## Implement or Refactor

```text
Implement [outcome] in [paths/components]. Read AGENTS.md and inspect Git status first.
Preserve unrelated changes and behavior outside this scope. Keep checks read-only and consumer
policy independent of Popo's development settings.
Constraints: [supported interfaces, compatibility, privacy, non-goals].
Acceptance: [observable behavior, diagnostics, exit statuses, tests].
Run [focused checks] and make check when practical; select artifact tests if packaging changes.
Update affected docs. Do not stage, commit, tag, publish, or change hosted settings implicitly.
Report the diff scope, evidence, checks run or skipped, failures, and remaining risks.
```

## Architecture or Interface Review

```text
Review [proposal/surface] against current implementation, tests, configuration, and docs.
Compare [alternatives]. Evaluate command/configuration compatibility, path resolution, malformed
inputs, diagnostics, exit statuses, read-only behavior, and consumer-policy boundaries.
Do not edit files or external state. Return evidence-backed findings, unresolved questions,
and a recommended decision. Distinguish demonstrated behavior from proposed behavior.
```

Use the [interface checklist] for contract-specific review and the [change-impact map] for scope.

## Documentation Synchronization

```text
Verify [claim/change] against canonical repository sources and update only affected maintained docs.
Scope: [paths]. Preserve purposeful project differences, headers, and historical release context.
Use reference links sorted by destination. Do not edit generated output or alter implementation
to make a documentation claim true. Run make docs-markdown; separately inspect reference-link
targets and factual accuracy. Report changes, evidence, skipped checks, and discrepancies requiring
an implementation decision. Do not introduce build tooling merely to mirror another repository.
```

## CI/CD Maintenance

```text
Update [specific workflow behavior] in [paths]. Inspect triggers, job/check names, permissions,
action pins, artifacts, and relevant tests before editing. Preserve least privilege, immutable
action references, credential-free ordinary checks, and intentional branch-routing policy.
Run the applicable repository checks and workflow-contract tests; review affected contributor,
branch-protection, and release documentation. Report local-validation limits explicitly.
Do not dispatch workflows, publish, tag, access secrets, or change hosted settings unless separately
authorized. Do not claim local tests prove hosted protections are enabled.
```

## Incident Diagnosis

```text
Diagnose [failed check/release/installation issue] without implementing changes.
Identify the first meaningful failure, affected revision or artifact, expected policy, and scope.
Use read-only evidence and safe local diagnostics; avoid exposing private repository content.
Do not rerun hosted workflows, change policy, delete artifacts, move tags, or publish.
Return the cause with supporting evidence, recovery options requiring approval, verification steps,
and documentation follow-up. Distinguish environment problems from checker or policy defects.
```

Use the [incident runbook] for triage and the [testing guide] to select meaningful validation.

[agent instructions]: ../../AGENTS.md
[testing guide]: ../TESTING.md
[interface checklist]: ../api/evolution-checklist.md
[change-impact map]: ../architecture/change-impact-map.md
[incident runbook]: ../runbooks/incident-response.md
[agent workflow]: agent-workflow.md
