<!--
pull_request_template.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Pull request template for scope, compatibility, validation, and safe delivery.

Responsibilities
- Capture change scope, compatibility risks, and validation evidence.
- Prompt safe delivery, synchronized documentation, and read-only CLI checks.

Maintainer Notes
- Keep guidance language- and platform-neutral; retain relevant CLI contracts.
- Keep local references aligned with the repository documentation.
-->

## Summary

<!-- Describe the user-visible or operational change and why it is needed. Link related issues and
identify the intended target branch when that context is not obvious. -->

## Compatibility and Risks

<!-- Describe effects on public interfaces, user-visible behavior, generated artifacts, supported
platforms or toolchains, and existing consumers or operations. Identify breaking changes,
deprecations, migrations, security considerations, and operational risks explicitly. For CLI changes,
include commands, flags, configuration, output, and exit codes. Write "None"
when there is no material impact. -->

## Validation

<!-- List the checks performed locally or in a representative environment and the relevant scenarios
exercised. Include commands and results when practical, such as `make check`, and identify checks
not run with the reason each was skipped. -->

## Deployment and Rollback

<!-- Describe deployment, publication, or release impact; configuration changes; and how to restore
the prior safe state. Write "None" when the change has no deployment or publication effect. -->

## Documentation and Decisions

<!-- List synchronized documentation. Link an ADR when the change alters an architectural boundary
or state why no ADR is needed. -->

## Checklist

- [ ] I added or updated tests for changed behavior when applicable.
- [ ] I updated user, maintainer, or deployment documentation where needed.
- [ ] I ran the relevant local checks.
- [ ] I updated `CHANGELOG.md` for a user-visible change.
- [ ] I reviewed public-interface, platform, artifact, and CLI output and exit-code compatibility.
- [ ] I identified breaking changes, deprecations, and migration steps explicitly.
- [ ] I described deployment, publication, and rollback implications when applicable.
- [ ] I reviewed `AGENTS.md` and preserved its safety invariants.
- [ ] I kept credentials, private identifiers, other secrets, and confidential evidence out of the
      repository.
- [ ] Packaging changes pass `make test-distribution test-installation`.
- [ ] Checks remain read-only and independent of consumer language or cloud.
- [ ] I documented intentional limitations and follow-up work.
