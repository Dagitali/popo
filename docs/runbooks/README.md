<!--
README.md
popo/docs/runbooks

Copyright © 2026 Dagitali LLC. All rights reserved.

Navigation for bounded operational diagnosis and recovery.

Maintainer Notes
- Distinguish verification from externally authorized recovery actions.
- Never include credentials or confidential incident evidence.
-->

# Runbooks

Runbooks provide operational response steps with evidence, safety boundaries, and verification.
Current procedures and supporting guidance:

- [Incident response]: Dependency drift, test/configuration mismatches, missing changelog entries,
  environment failures, and publication problems.
- [Branch protection]: Required-check selection and hosted-policy configuration guidance.
- [Release playbook]: Candidate preparation and authorized release operations.

Popo's checks and installation workflows do not deploy cloud resources. Do not import a cloud
cleanup procedure into this project or infer authorization to modify a consumer repository. Preserve
exact tags and artifact identity when investigating failures.

[Branch protection]: ../../.github/BRANCH-PROTECTION.md
[Release playbook]: ../playbooks/release.md
[Incident response]: incident-response.md
