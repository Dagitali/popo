<!--
agent-workflow.md
popo/docs/development

Copyright © 2026 Dagitali LLC. All rights reserved.

Evidence-backed handoff from design discussion to bounded repository work.

Maintainer Notes
- Keep this workflow independent of any assistant vendor or editor.
- Treat AGENTS.md as authoritative for repository-specific agent duties.
-->

# Agent-Assisted Development Workflow

Use design discussion and repository execution as complementary activities. This workflow applies
regardless of the assistant or editor used; the [agent instructions] define repository obligations.

- [Explore the Decision](#explore-the-decision)
- [Ground the Work](#ground-the-work)
- [Prepare the Handoff](#prepare-the-handoff)
- [Execute and Verify](#execute-and-verify)

## Explore the Decision

Before requesting edits, clarify outcomes, constraints, alternatives, and acceptance criteria.
Consider CLI compatibility, consumer policy, privacy, failure behavior, and maintenance cost.
Separate an agreed requirement from a suggestion or unresolved question.

A conversational recommendation is not repository evidence. Commands, configuration defaults,
supported versions, workflow behavior, and release status must be verified against the checkout. Do
not include credentials or private consumer content in a task brief.

## Ground the Work

Use repository inspection to establish what currently exists and whether a proposed change fits
Popo's read-only checker boundary. Read relevant implementation, tests, configuration, and docs; use
the [change-impact map] to identify dependent surfaces.

Distinguish review from implementation: a request to diagnose or compare does not authorize a fix.
Repository editing likewise does not authorize publishing packages, creating tags, changing hosted
settings, or mutating protected branches. Resolve conflicting evidence before expanding scope.

## Prepare the Handoff

A useful task brief contains:

1. Desired outcome and explicit non-goals;
2. Relevant paths, commands, configuration keys, or observed failures;
3. Alternatives considered and unresolved decisions;
4. Compatibility, privacy, read-only operation, and consumer-ownership constraints; and
5. Observable acceptance criteria and appropriate local validation.

Use the [task templates] as starting points, not as permission to perform every listed activity.
Keep Popo's own Python and dependency policy separate from policies it validates for consumers.

## Execute and Verify

1. Read applicable instructions and inspect Git status; preserve unrelated and staged work.
2. Confirm canonical sources and state the intended file scope and verification plan.
3. Make the smallest coherent change within the requested authority.
4. Run focused checks from the [testing guide], then `make check` when practical. Use artifact gates
   for packaging changes rather than treating source tests as installation evidence.
5. Synchronize affected documentation using the [documentation synchronization guide]. For Markdown,
   run `make docs-markdown` and separately inspect undefined reference labels, images, and factual
   claims.
6. Review the diff for unrelated changes, generated files, private data, and documentation drift.
7. Report changed files, evidence, completed and skipped checks, failures, and remaining risks.

Record durable interface decisions in the maintained interface or configuration guidance, and
reusable failure/recovery steps in the [incident runbook]. Do not create placeholder decision
records or additional policy documents solely to match another project's tree. Follow the [release
playbook] when an explicitly requested task involves release preparation; successful local checks
alone do not prove hosted release or publication success.

[agent instructions]: ../../AGENTS.md
[documentation synchronization guide]: ../../CONTRIBUTING.md#documentation-synchronization
[testing guide]: ../TESTING.md
[change-impact map]: ../architecture/change-impact-map.md
[release playbook]: ../playbooks/release.md
[incident runbook]: ../runbooks/incident-response.md
[task templates]: task-templates.md
