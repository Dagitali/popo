<!--
DESIGN.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Design principles and compatibility constraints for reusable repository checks.

Maintainer Notes
- Keep claims grounded in repository sources and preserve consumer-owned policy.
- Link to detailed guidance rather than maintaining competing copies.
-->

# Design

This document records the design constraints evident in Popo's implementation and contributor
policy. [Architecture] describes the resulting components and execution flow.

- [Goals and Non-Goals](#goals-and-non-goals)
- [Public Interface](#public-interface)
- [Configuration Strategy](#configuration-strategy)
- [Testing and Change Safety](#testing-and-change-safety)
- [Decision Recording and Evolution](#decision-recording-and-evolution)

## Goals and Non-Goals

Provide reusable, deterministic checks with clear findings and consistent local/CI invocation. Keep
consumer policy explicit and independent of Popo's own development setup.

Automatic repairs, deployment, hosted-rule administration, remote code execution, and a universal
workflow or Markdown interpreter are outside the current checker boundary. New capabilities need a
demonstrated requirement and a documented scope; similarity to another project is not sufficient.

## Public Interface

The CLI, documented configuration, diagnostics, exit codes, and intentional package-root exports are
compatibility considerations. The package root exports only `__version__`; internal checker
functions are not a promised consumer API. Prefer CLI examples for adoption.

Stricter validation can break previously passing consumer CI even when command signatures stay the
same. Review accepted inputs, defaults, failure behavior, and migration requirements together using
the [interface checklist].

## Configuration Strategy

Keep configuration models and parsing grouped by policy domain under `src/popo/config/`. Shared
parsing belongs in internal helpers, while the package facade keeps intentional exports explicit.
Consumer settings live under `[tool.popo]`; package/tool metadata remains canonical in
`pyproject.toml`.

Preserve purposeful differences between domains: automation settings reject unknown keys and are
opt-in for aggregate checking, while dependency and Python-policy settings retain their documented
defaults and unknown-key handling. Path resolution is command-specific; consult the [configuration
reference] rather than assuming every relative path uses the same base.

When extending configuration:

1. Establish a consumer requirement and define accepted inputs, defaults, and failure behavior.
2. Implement parsing in the owning domain and preserve its existing compatibility rules.
3. Keep repository-file checks in the owning validator and expose only the interfaces needed.
4. Cover valid, invalid, missing, and boundary inputs, including standalone and aggregate dispatch.
5. Update the configuration reference, adoption examples, and changelog as applicable.

Use the [interface checklist] for the full review, including migration and release classification.

## Testing and Change Safety

Keep unit and integration tests independent of credentials and network access. Exercise malformed
inputs and read-only behavior alongside successful cases. Artifact tests separately validate package
contents and installed entry points outside the checkout.

Use focused Make targets while iterating, then `make check`. Packaging changes additionally need
distribution and installation checks. Coverage is diagnostic; Popo does not inherit another
project's coverage threshold, infrastructure tests, or documentation build system.

## Decision Recording and Evolution

Record accepted interface decisions in the relevant maintained guide and changelog. Capture reusable
troubleshooting outcomes in [learnings] and detailed operational recovery in runbooks. A separate
decision record is useful when alternatives or lasting tradeoffs need independent history; do not
create empty records solely to match another repository.

Prefer additive, optional settings when they satisfy the requirement. Preserve read-only operation,
consumer ownership, immutable action pins, and least-privilege automation. Follow the [release
policy] for versioned changes, and document intentional compatibility breaks explicitly.

[Architecture]: ARCHITECTURE.md
[learnings]: LEARNINGS.md
[release policy]: RELEASE-POLICY.md
[configuration reference]: docs/CONFIGURATION.md
[interface checklist]: docs/api/evolution-checklist.md
