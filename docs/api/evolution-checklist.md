<!--
evolution-checklist.md
popo/docs/api

Copyright © 2026 Dagitali LLC. All rights reserved.

Review checklist for public CLI, configuration, and package-interface changes.

Maintainer Notes
- Preserve read-only behavior and consumer-owned policy.
- Require evidence for compatibility claims rather than adding support promises.
-->

# Public API Evolution Checklist

Use this checklist for commands, flags, configuration keys, defaults, validation, diagnostics, exit
codes, and intentional package-root exports. Even a stricter check can break a consumer's CI.

- [Establish the Contract](#establish-the-contract)
- [Implement and Prove](#implement-and-prove)
- [Synchronize Documentation](#synchronize-documentation)
- [Validate and Report](#validate-and-report)

## Establish the Contract

- Identify the demonstrated consumer need or correctness defect.
- Classify the change as additive, behavior-changing, deprecating, or breaking; review the [release
  policy] and state any required migration without inventing compatibility guarantees.
- Define accepted inputs, defaults, failure messages, and exit behavior before implementation.
- Keep consumer policy independent of Popo's tool versions, repository layout, and cloud choices.
- Preserve read-only checks; propose any new mutation capability as a separate design decision.

## Implement and Prove

- Keep CLI parsing, configuration loading, checker logic, and reporting cohesive and separate.
- Update typed docstrings and intentional exports only when their contracts change.
- Add unit cases for valid input, invalid input, missing files, and changed boundary conditions.
- Exercise dispatch and reported results through CLI integration tests, including `check-all`
  behavior when applicable. Do not assume individual-command options also exist on `check-all`.
- Check both console and module entry points for packaging or installed-interface changes.
- Test generic policies independently of Popo's own dependency pins; retain the repository
  self-check for actual metadata consistency.

## Synchronize Documentation

Review the [configuration reference], README examples, changelog, and affected release record.
Update only changed claims and preserve existing anchors when reorganizing guides. Follow the
[documentation synchronization guide] for ownership and link validation instead of creating a second
configuration reference.

## Validate and Report

Run `make lint typecheck test-unit test-integration`, then `make check` and `make docs-markdown`.
Use the [testing guide] for additional artifact or installation checks and the [release playbook]
for candidate evidence. Local checks do not establish hosted publication or protection settings.

Report compatibility effects, completed checks, known failures, and outstanding release work. Do not
weaken tests merely to preserve a passing result after changing the intended contract.

[documentation synchronization guide]: ../../CONTRIBUTING.md#documentation-synchronization
[release policy]: ../../RELEASE-POLICY.md
[configuration reference]: ../CONFIGURATION.md
[testing guide]: ../TESTING.md
[release playbook]: ../playbooks/release.md
