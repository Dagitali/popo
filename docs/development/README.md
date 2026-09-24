<!--
README.md
popo/docs/development

Copyright © 2026 Dagitali LLC. All rights reserved.

Navigation for contributor setup and development guidance.

Maintainer Notes
- Keep commands aligned with Make and canonical tool configuration.
- Link to existing contributor policies instead of copying them.
-->

# Development Documentation

Use this directory for contributor explanations beyond the root [contributing guide] and [agent
instructions]. Start with onboarding, then choose the guide for the area being changed.

- [Developer onboarding]: First local session, repository orientation, and safe CLI use.
- [Interface evolution]: Review changes to commands, configuration, and compatibility.
- [Testing guide]: Focused checks, dependency boundaries, and artifact validation.
- [Documentation synchronization]: Sources of truth and maintained documentation to review.
- [Documentation validation]: Local Markdown checks and their limits.
- [Release playbook]: Candidate evidence and publication boundaries.

Do not copy consumer policy into Popo's development configuration merely to make examples pass. Keep
tests deterministic and preserve unrelated working-tree changes.

[agent instructions]: ../../AGENTS.md
[contributing guide]: ../../CONTRIBUTING.md
[Documentation synchronization]: ../../CONTRIBUTING.md#documentation-synchronization
[Documentation validation]: ../README.md#validate-documentation
[Testing guide]: ../TESTING.md
[Interface evolution]: ../api/evolution-checklist.md
[Release playbook]: ../playbooks/release.md
[Developer onboarding]: onboarding.md
