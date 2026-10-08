<!--
ROADMAP.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Current foundations and evidence required for future scope decisions.

Maintainer Notes
- Keep claims grounded in repository sources and preserve consumer-owned policy.
- Link to detailed guidance rather than maintaining competing copies.
-->

# Roadmap

This is the canonical active roadmap for planning and readiness. Priorities depend on consumer
evidence rather than a fixed release schedule or a commitment to new features. Current
implementation is described by the [README]; version-specific scope and validation belong in the
[release archive]. Keep completed work in those records and current priorities here.

- [Current Foundations](#current-foundations)
- [Near-Term Review](#near-term-review)
- [Before Broader Publication](#before-broader-publication)
- [Future Opportunities](#future-opportunities)

## Current Foundations

- Read-only Markdown, action-pin, automation-contract, dependency, Python-policy, and changelog
  checks.
- Consumer-owned configuration, typed implementation, and a shared CLI for local and CI use.
- Unit/integration gates plus explicit distribution and clean-install tests.
- Dependency-boundary CI, optional audits, SBOM generation, and guarded GitHub publication.
- Markdown guides, adoption procedures, incident runbooks, and release records.

These describe the current source; consult versioned notes before assuming a released tag contains
every capability in the working development line.

## Near-Term Review

Use the [adoption playbook] to compare Popo with a consumer's existing checks before retiring them.
Collect small, sanitized fixtures for unsupported behavior or compatibility gaps. Prioritize
demonstrated requirements and preserve consumer-specific policies instead of importing them into
generic validators.

Keep configuration, diagnostics, docs, and regression cases synchronized. Use the [interface
checklist] to decide whether a proposed extension changes an existing contract.

## Before Broader Publication

Any proposal to publish to an additional package index needs explicit authorization, confirmed
package ownership, a reviewed publication mechanism, and installation validation from the published
artifacts. PyPI publication is not currently configured.

Before claiming stable support, define the public compatibility boundary, maintenance expectations,
deprecation policy, and representative consumer evidence. No stable-release date or support window
is promised here. The [release policy] remains authoritative for current delivery.

## Future Opportunities

Consider additional formats or policy domains only when repeatable consumer evidence establishes
their inputs, ownership, failure behavior, and test strategy. Evaluate extensions against [design
guidance]. Automatic fixes, cloud operations, and hosted administration would require separate scope
decisions; they are not implied by this roadmap.

[design guidance]: DESIGN.md
[README]: README.md
[release policy]: RELEASE-POLICY.md
[adoption playbook]: docs/playbooks/adopt-popo.md
[release archive]: docs/releases/README.md
[interface checklist]: https://github.com/Dagitali/engineering/blob/main/interfaces/evolution-checklist.md
