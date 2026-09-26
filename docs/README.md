<!--
README.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Navigation for maintained consumer, contributor, and release documentation.

Maintainer Notes
- Link to canonical guidance rather than maintaining duplicate policies.
- Do not imply that Sphinx builds or cloud deployment guides exist for this CLI.
-->

# Documentation

Use this directory for maintained guides and reference material. Repository governance stays at the
root or under `.github/` so contributors and GitHub can discover its conventional locations.

- [Document Scope](#document-scope)
- [Start Here](#start-here)
- [Validate Documentation](#validate-documentation)
- [Guides](#guides)
- [Topic Indexes](#topic-indexes)
- [Related Repository Documents](#related-repository-documents)

## Document Scope

Guides describe Popo's actual CLI and repository policy. Consumer configuration is independent of
Popo's development conventions. Historical release records preserve their preparation context;
current source, tests, workflows, and maintained guides establish present behavior.

The scope intentionally differs from infrastructure projects: consumer cloud operations, deployment
cost estimates, and construct-specific architecture records do not belong here. API notes describe
Popo's supported interfaces without duplicating generated reference material. Release records cover
Popo's own history, not another package's versions. Documentation synchronization remains in
[Contributing] rather than a competing policy file; operational guidance links to the existing
branch-protection and release policies.

## Start Here

| Need | Document |
| --- | --- |
| Install and run the CLI | [Project overview] |
| Try a check and diagnose a failure | [First repository tutorial] |
| Configure a consumer repository | [Configuration reference] |
| Adopt checks or replace local scripts | [Adoption playbook] |
| Change a public interface | [Interface evolution] |
| Scope implementation and review work | [Change-impact map] |
| Coordinate a change through validation | [Change management] |
| Substantiate a public technical claim | [Evidence inventory template] |
| Set up development | [Developer onboarding] and [development setup] |
| Choose tests and quality gates | [Testing guide] |
| Prepare a release | [Release playbook] and [release policy] |
| Inspect versioned changes | [Changelog] and [release archive] |
| Work with an automated agent | [Agent instructions], [agent workflow], and [task templates] |
| Diagnose CI or release failures | [Incident response] |
| Coordinate required-check changes | [Update required checks] |

## Validate Documentation

After installing development dependencies, run from the repository root:

```console
make docs-markdown
```

This checks local inline-link and reference-definition destinations, heading anchors, and explicit
HTML anchors. It does not detect undefined reference labels or validate inline image links, external
URL availability, or factual accuracy. Review those separately. Popo does not currently configure a
Sphinx site or HTML/EPUB build targets. Markdown is the maintained documentation format; do not copy
generated output from another project.

## Guides

- [First repository tutorial]: A consumer's first successful check, deliberate failure, and repair.
- [Configuration reference]: Input paths, dependency modes, Python-policy defaults, and CLI scope.
- [Adoption playbook]: Consumer setup, behavioral comparison, CI integration, and migration safeguards.
- [Change-impact map]: Source ownership, verification, and documentation affected by a change.
- [Change management]: Classify work and connect implementation, documentation, and release evidence.
- [Evidence inventory template]: Optional record of sources, limitations, and disclosure decisions.
- [Testing guide]: Selecting deterministic checks and opt-in artifact validation.
- [Developer onboarding]: First local session, source orientation, and safe consumer checks.
- [Incident response]: Triage and recovery for policy, environment, artifact, and release failures.
- [Update required checks]: Safe transitions and verification of hosted check requirements.
- [Release playbook]: Candidate preparation, validation, authorized publication, and closeout.
- [Release archive]: Detailed records for versioned changes.

## Topic Indexes

- [API notes]: Public-interface boundaries and evolution checklist.
- [Architecture notes]: Component boundaries and change-impact review.
- [Development documentation]: Onboarding, testing, and contributor reference links.
- [Playbooks]: Repeatable maintainer workflows.
- [Runbooks]: Bounded operational diagnosis and recovery.
- [Tutorials]: End-to-end consumer learning paths.

## Related Repository Documents

- [Contributing]: Workflow, tool setup, dependency updates, and review expectations.
- [Documentation synchronization]: Sources of truth and documentation ownership.
- [Branch protection]: Configurable routing and proposed hosted protections.
- [Tests overview]: Authoritative test-layer layout and fixture conventions.

Use reference links sorted by destination and keep file headers and tables of contents current.

[Branch protection]: ../.github/BRANCH-PROTECTION.md
[Agent instructions]: ../AGENTS.md
[Changelog]: ../CHANGELOG.md
[Contributing]: ../CONTRIBUTING.md
[Development setup]: ../CONTRIBUTING.md#development-setup
[Documentation synchronization]: ../CONTRIBUTING.md#documentation-synchronization
[Project overview]: ../README.md
[release policy]: ../RELEASE-POLICY.md
[Tests overview]: ../tests/README.md
[Configuration reference]: CONFIGURATION.md
[Evidence inventory template]: EVIDENCE_INVENTORY_TEMPLATE.md
[Testing guide]: TESTING.md
[API notes]: api/README.md
[Interface evolution]: api/evolution-checklist.md
[Architecture notes]: architecture/README.md
[Change-impact map]: architecture/change-impact-map.md
[Development documentation]: development/README.md
[agent workflow]: development/agent-workflow.md
[Developer onboarding]: development/onboarding.md
[task templates]: development/task-templates.md
[Playbooks]: playbooks/README.md
[Adoption playbook]: playbooks/adopt-popo.md
[Change management]: playbooks/change-management.md
[Release playbook]: playbooks/release.md
[release archive]: releases/README.md
[Runbooks]: runbooks/README.md
[Incident response]: runbooks/incident-response.md
[Update required checks]: runbooks/update-required-checks.md
[Tutorials]: tutorials/README.md
[First repository tutorial]: tutorials/check-first-repository.md
