<!--
engineering.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Shared-document replacements and Popo-owned documentation boundaries.

Maintainer Notes
- Link shared sources directly rather than retaining duplicate adapters.
- Preserve project contracts, community-health files, and agent instructions.
-->

# Shared Engineering Guidance

Reusable engineering procedures and blank templates live in Dagitali Engineering. Popo removes local
equivalents and links directly to the shared files. Sources were reviewed in the sibling
`../engineering/` checkout. GitHub links follow Engineering's `main` branch so contributors use the
current shared guidance without requiring a sibling clone.

- [Replaced Documents](#replaced-documents)
- [Retained Local Authority](#retained-local-authority)
- [Updates and Recovery](#updates-and-recovery)
- [Validation](#validation)

## Replaced Documents

| Removed Popo file | Engineering equivalent |
| --- | --- |
| `docs/development/agent-workflow.md` | [development/agent-assisted-workflow.md](https://github.com/Dagitali/engineering/blob/main/development/agent-assisted-workflow.md) |
| `docs/development/task-templates.md` | [templates/development-task.md](https://github.com/Dagitali/engineering/blob/main/templates/development-task.md) |
| `docs/development/README.md` | [development/README.md](https://github.com/Dagitali/engineering/blob/main/development/README.md) |
| `docs/playbooks/change-management.md` | [playbooks/change-management.md](https://github.com/Dagitali/engineering/blob/main/playbooks/change-management.md) |
| `docs/api/evolution-checklist.md` | [interfaces/evolution-checklist.md](https://github.com/Dagitali/engineering/blob/main/interfaces/evolution-checklist.md) |
| `docs/runbooks/update-required-checks.md` | [runbooks/update-required-checks.md](https://github.com/Dagitali/engineering/blob/main/runbooks/update-required-checks.md) |
| `docs/EVIDENCE_INVENTORY_TEMPLATE.md` | [templates/evidence-inventory.md](https://github.com/Dagitali/engineering/blob/main/templates/evidence-inventory.md) |
| `.github/RELEASE-NOTES-TEMPLATE.md` | [templates/releases/python-package.md](https://github.com/Dagitali/engineering/blob/main/templates/releases/python-package.md) |
| `LEARNINGS.md` | [learnings/python-and-repository-tooling.md](https://github.com/Dagitali/engineering/blob/main/learnings/python-and-repository-tooling.md) |
| `REFERENCES.md` | [REFERENCES.md](https://github.com/Dagitali/engineering/blob/main/REFERENCES.md) |
| `docs/playbooks/release.md` | [playbooks/release.md](https://github.com/Dagitali/engineering/blob/main/playbooks/release.md) |
| `docs/runbooks/incident-response.md` | [runbooks/repository-ci-incident.md](https://github.com/Dagitali/engineering/blob/main/runbooks/repository-ci-incident.md) |
| `docs/TESTING.md` | [testing/python.md](https://github.com/Dagitali/engineering/blob/main/testing/python.md) |
| `docs/development/onboarding.md` | [development/onboarding.md](https://github.com/Dagitali/engineering/blob/main/development/onboarding.md) |

Navigation and reference links now target these equivalents. Historical release descriptions retain
their original change claims; their template links resolve to the shared source instead of a deleted
local file. No local redirect or adapter documents remain for the replaced files.

## Retained Local Authority

README entry points, community-health files (`README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, and
`SUPPORT.md`), `AGENTS.md`, and installed Copilot instructions remain committed locally. Licensing
files and notices retain their existing authority.

Popo-specific architecture, design, source-impact map, configuration, checker guides, consumer
adoption tutorial/playbook, contributor setup, test layout and commands, workflow map, branch-routing
configuration, release policy/archive, and contributor recovery notes stay beside their
implementation. Engineering's own root policies are policies for that documentation repository, not
replacements for Popo's contracts. Shared examples do not impose tool versions, GitFlow routes,
support promises, publication behavior, or authority to mutate consumer repositories.

When using the shared interface checklist or task briefs, apply Popo's read-only checker boundary,
consumer-independent policy, CLI diagnostics/exit contracts, and Make validation targets from [agent
instructions] and [contributing]. Use the shared release template to create
`docs/releases/vMAJOR.MINOR.PATCH.md`; retain Popo's existing record headings, dated changelog
links, and release-specific evidence as required by the [release policy].

## Updates and Recovery

The maintainer owns replacement review. Links follow Engineering's `main` branch; review shared
changes against local requirements and inspect its license/notices when adopting new material.
Completed Popo records remain in this repository; private operator evidence stays access-controlled.
Shared files are referenced rather than copied, and their [license and notices] remain at the
source.

Run `make docs-markdown` and `make check`; separately verify shared paths/anchors, reference labels,
and factual claims. Restore a removed document through a reviewed revert only if a shared equivalent
cannot preserve a required local contract. Do not restore duplicate guidance merely to retain a
path.

## Validation

The testing/onboarding replacement passed `make docs-markdown`, `make check` (426 tests and all
static/repository checks), shared-path verification, and `git diff --check` on 2026-10-08. Artifact
checks were skipped because package behavior and metadata are unchanged.

The additional four-file replacement passed `make docs-markdown`, `make check` (426 tests and
all static/repository checks), shared-path verification, and `git diff --check` on 2026-10-08.
Artifact checks were skipped because this change affects documentation only.

On 2026-10-08, this migration passed `make docs-markdown`, `make check` (426 unit/integration tests,
lint, formatting, strict typing, and repository checks), and `git diff --check`. Shared paths and
anchors were verified against the inspected Git revision in the sibling repository; those checks do
not establish the contents of the live `main` branch. Artifact checks were skipped because package
behavior and metadata are unchanged. Local Markdown checks do not verify external availability. The
previous GitHub page fetch failed, so remote availability remains unverified. No implementation,
workflow, hosted-setting, package metadata, or publication changes are included.

[agent instructions]: ../AGENTS.md
[contributing]: ../CONTRIBUTING.md
[release policy]: ../RELEASE-POLICY.md
[license and notices]: https://github.com/Dagitali/engineering/blob/main/README.md#license
