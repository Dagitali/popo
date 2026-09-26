<!--
README.md
popo/docs/architecture

Copyright © 2026 Dagitali LLC. All rights reserved.

Architecture navigation and ownership boundaries for the repository-policy CLI.

Maintainer Notes
- Keep implementation evidence separate from proposed design changes.
- Do not import consumer deployment topology into reusable checker documentation.
-->

# Architecture Notes

The [architecture overview] introduces command dispatch, configuration, validation, and reporting.
Use the [change-impact map] to identify the implementation, tests, and documentation affected by a
proposed change, and the [interface checklist] when public behavior changes.

Popo owns reusable checks and their diagnostics. Consumer repositories own policy values, build
systems, branching conventions, and deployment operations. A new check should not implicitly
transfer those responsibilities into Popo.

Keep focused architectural notes grounded in current source and tests. Separate proposed behavior
from implemented behavior, explain compatibility consequences, and keep private consumer details out
of tracked documents. Generated API pages and cloud infrastructure diagrams are not part of this
documentation setup.

[architecture overview]: ../../README.md#architecture
[interface checklist]: ../api/evolution-checklist.md
[change-impact map]: change-impact-map.md
