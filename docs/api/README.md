<!--
README.md
popo/docs/api

Copyright © 2026 Dagitali LLC. All rights reserved.

Public-interface scope and design-note navigation.

Maintainer Notes
- Treat CLI behavior and consumer configuration as compatibility surfaces.
- Do not advertise internal checker functions as a stable Python API.
-->

# API Documentation

Popo's primary consumer interface is the `popo` CLI, also available through `python -m popo`.
Commands, flags, configuration, diagnostics, and exit codes are compatibility considerations. The
package root currently exports only `__version__` through `__all__`; internal checker modules are
not a promised consumer API.

- [CLI quickstart]: Commands and entry points.
- [Configuration reference]: Settings, defaults, path resolution, and validation boundaries.
- [Interface evolution checklist]: Implement public changes with matching tests and documentation.
- [Public API guidance]: Typing and compatibility review conventions.

There is no generated Sphinx API reference configured here. Keep source docstrings accurate and link
to maintained guidance rather than duplicating implementation details.

[Public API guidance]: ../../CONTRIBUTING.md#public-api-and-type-checking
[CLI quickstart]: ../../README.md#quickstart
[Configuration reference]: ../CONFIGURATION.md
[Interface evolution checklist]: evolution-checklist.md
