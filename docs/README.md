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
- [Related Repository Documents](#related-repository-documents)

## Document Scope

Guides describe Popo's actual CLI and repository policy. Consumer configuration is independent of
Popo's development conventions. Historical release records preserve their preparation context;
current source, tests, workflows, and maintained guides establish present behavior.

## Start Here

| Need | Document |
| --- | --- |
| Install and run the CLI | [Project overview] |
| Configure a consumer repository | [Configuration reference] |
| Set up development | [Developer onboarding] and [development setup] |
| Choose tests and quality gates | [Testing guide] |
| Prepare a release | [Release playbook] and [release policy] |
| Inspect versioned changes | [Changelog] and [release archive] |
| Work with an automated agent | [Agent instructions] |
| Diagnose CI or release failures | [Incident response] |

## Validate Documentation

After installing development dependencies, run from the repository root:

```console
make docs-markdown
```

This checks local paths and heading anchors, not external URL availability or factual accuracy. Popo
does not currently configure a Sphinx site or HTML/EPUB build targets. Markdown is the maintained
documentation format; do not copy generated output from another project.

## Guides

- [Configuration reference]: Input paths, dependency modes, Python-policy defaults, and CLI scope.
- [Testing guide]: Selecting deterministic checks and opt-in artifact validation.
- [Developer onboarding]: First local session, source orientation, and safe consumer checks.
- [Incident response]: Triage and recovery for policy, environment, artifact, and release failures.
- [Release playbook]: Candidate preparation, validation, authorized publication, and closeout.
- [Release archive]: Detailed records for versioned changes.

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
[Testing guide]: TESTING.md
[Developer onboarding]: development/onboarding.md
[Release playbook]: playbooks/release.md
[release archive]: releases/README.md
[Incident response]: runbooks/incident-response.md
