<!--
change-management.md
popo/docs/playbooks

Copyright © 2026 Dagitali LLC. All rights reserved.

Change classification, implementation boundaries, documentation, and release evidence.

Maintainer Notes
- Link to authoritative checklists instead of duplicating their requirements.
- Keep consumer policy and external operations outside implicit change scope.
-->

# Change Management Playbook

Use this playbook to take a proposed change from a bounded requirement to a verified handoff. The
[contributing guide] owns review policy; the linked checklists supply detailed procedures.

- [Classify the Change](#classify-the-change)
- [Scaffold Only Supported Behavior](#scaffold-only-supported-behavior)
- [Synchronize Documentation](#synchronize-documentation)
- [Release and Recovery Evidence](#release-and-recovery-evidence)

## Classify the Change

| Class | Examples | Evidence to obtain |
| --- | --- | --- |
| Public interface | Commands, flags, defaults, diagnostics, exports | Contract tests and compatibility review |
| Checker behavior | Accepted inputs, path discovery, policy validation | Positive, negative, and boundary cases plus CLI integration |
| Packaging | Dependencies, interpreter support, distributions | Dependency-policy checks, artifact and clean-install tests |
| Delivery | Workflow triggers, job names, permissions, artifacts | Workflow contracts, pin checks, authorized hosted verification |
| Documentation | Guides, examples, claims, links | Canonical-source review, link and example validation |

Use the [change-impact map] to identify the affected sources, tests, and docs. Changes spanning
classes need evidence for every applicable boundary. State what will remain unchanged before
editing; do not expand a documentation or diagnosis task into an implementation change.

## Scaffold Only Supported Behavior

Before introducing a component, option, example, or automation entry point, define its demonstrated
need, single responsibility, owner, supported inputs, failure behavior, and focused verification.
Use the [interface checklist] for public-contract decisions, including stricter checks that can
break previously passing consumer CI.

Keep reusable validation separate from consumer-specific policy and deployment choices. Preserve
read-only checking; do not add automatic repair, speculative plugin systems, placeholder services,
or platform assumptions just to match another project's structure. Consumer fixtures should prove
generic behavior independently of Popo's own dependency versions and repository layout.

Select checks using the [testing guide]. Run focused checks while iterating and `make check` when
practical. Packaging changes additionally need artifact and clean-install validation; source tests
alone cannot establish installed behavior. Keep unrelated and generated files out of the diff.

## Synchronize Documentation

Follow the [documentation synchronization guide] during implementation. Use the impact map's
ownership table rather than maintaining another copy here. Search for affected commands, keys, and
claims, then update the smallest complete set of maintained explanations and examples.

Preserve file headers, useful anchors, and historical release context. Use bottom-of-document
reference links sorted by destination. Run `make docs-markdown`, separately check reference-link
targets, and verify factual claims against their sources. The checker does not validate reference
definitions, external availability, or factual accuracy.

For changed required job names or event coverage, follow the [required-check runbook]. Local
workflow validation is not proof of hosted enforcement. Do not change implementation, hosted
settings, or release behavior merely to make prose true; report conflicting evidence instead.

## Release and Recovery Evidence

For a release, use the [release playbook] and [release notes template]. Record the exact candidate,
scope, compatibility effects, migration requirements, completed checks, and outstanding work.
Distinguish local validation, hosted validation, and publication rather than treating them as one
successful operation.

Identify a recovery path appropriate to the change: a reviewed fix or revert for source, coordinated
workflow/rules restoration for check transitions, or a new version for a released defect. Preserve
existing tag identities. Use the [incident runbook] when the cause is unresolved rather than
weakening policy to get a passing result.

No step authorizes publication, tag creation, protected-branch mutation, secret access, or changes
to consumer repositories. Obtain explicit authorization for external actions and report checks that
were skipped or failed. Keep confidential evidence in an appropriate private record.

[release notes template]: ../../.github/RELEASE-NOTES-TEMPLATE.md
[contributing guide]: ../../CONTRIBUTING.md
[documentation synchronization guide]: ../../CONTRIBUTING.md#documentation-synchronization
[testing guide]: ../TESTING.md
[interface checklist]: ../api/evolution-checklist.md
[change-impact map]: ../architecture/change-impact-map.md
[incident runbook]: ../runbooks/incident-response.md
[required-check runbook]: ../runbooks/update-required-checks.md
[release playbook]: release.md
