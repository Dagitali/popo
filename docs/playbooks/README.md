<!--
README.md
popo/docs/playbooks

Copyright © 2026 Dagitali LLC. All rights reserved.

Navigation for repeatable maintainer workflows.

Maintainer Notes
- Include only supported procedures with explicit validation boundaries.
- Keep secrets and operator-only evidence out of tracked files.
-->

# Playbooks

Playbooks describe goal-oriented workflows involving several decisions or validation steps. Current
procedures and related guidance:

- [Change management]: Classify work, preserve boundaries, and assemble validation and release
  evidence.
- [Release checklist]: Prepare, validate, obtain authorization, and close out a release.
- [Interface evolution]: Plan and verify changes to the public CLI and configuration.
- [Testing guide]: Select the checks required for the change.
- [Incident response]: Diagnose and recover when validation or release work fails.

These procedures do not authorize publication, tag creation, or hosted-setting changes. Follow the
[release policy] for delivery safeguards. Add new playbooks only for concrete workflows, not to
mirror an unrelated project's directory count.

[release policy]: ../../RELEASE-POLICY.md
[Testing guide]: ../TESTING.md
[Interface evolution]: ../api/evolution-checklist.md
[Incident response]: ../runbooks/incident-response.md
[Change management]: change-management.md
[Release checklist]: release.md
