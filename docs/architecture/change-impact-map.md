<!--
change-impact-map.md
popo/docs/architecture

Copyright © 2026 Dagitali LLC. All rights reserved.

Source, validation, and documentation ownership for scoped repository changes.

Maintainer Notes
- Keep source paths and commands synchronized with the checkout.
- Use the smallest complete review scope without weakening quality gates.
-->

# Change-Impact Map

Use this map to identify the minimum complete change set. It describes review paths, not a second
implementation specification. Source, tests, Make targets, and workflows remain executable truth.
Paths below are relative to the repository root.

- [Changed Surfaces](#changed-surfaces)
- [Review Lenses](#review-lenses)
- [Boundary Rules](#boundary-rules)

## Changed Surfaces

| Changed surface | Evidence to inspect | Focused validation | Documentation to review |
| --- | --- | --- | --- |
| Commands, flags, dispatch | `src/popo/cli.py`, `tests/integration/test_i_cli.py` | `make test-integration` | README quickstart, configuration, changelog |
| Configuration keys or defaults | `src/popo/config/`, `tests/unit/configs/`, `tests/unit/checks/test_u_automation.py` | Unit and CLI integration tests | Configuration reference, README examples, release notes |
| Checker behavior | `src/popo/checks/`, corresponding unit suite | Matching unit suite and CLI integration tests | Checker scope, configuration, compatibility notes |
| Shared reporting or file discovery | `src/popo/support.py`, callers, support tests | All affected checkers and CLI tests | Architecture overview, diagnostics, documented exclusions |
| Public exports or typing | `src/popo/__init__.py`, `src/popo/py.typed`, artifact tests | Typecheck and distribution tests | API notes, public docstrings, release notes |
| Dependencies or Python support | `pyproject.toml`, `requirements/lowest.txt`, `.python-version`, CI matrix | Dependency/Python policy and boundary tests | README requirements, testing, changelog |
| Make targets or test selection | `Makefile`, `tests/conftest.py`, Make tests, CI callers | Changed target and `make check` | Contributor guide, tests overview, onboarding |
| Workflow or composite action | `.github/workflows/`, `.github/actions/`, workflow tests | Pin checks, relevant unit contracts, `actionlint` | Branch protection, contributor guidance, release policy |
| Packaging or release artifacts | Build metadata, CD workflow, artifact fixtures | Distribution and clean-install tests | Release policy, playbook, release records |
| Documentation only | Canonical sources for each changed claim | `make docs-markdown` and diff review | Indexes, reference links, affected examples |

Use the [testing guide] to choose commands and the [documentation synchronization guide] to locate
maintained mirrors. Changes spanning multiple rows need all applicable evidence. Follow focused
checks with `make check` when practical; publication-sensitive changes also require release gates.

## Review Lenses

For CLI and configuration changes, assess defaults, path resolution, missing or malformed inputs,
diagnostic compatibility, exit status, and whether a stricter check breaks existing consumer CI. Use
the [interface checklist] for public-contract decisions.

For dependency changes, distinguish the versions Popo supports from arbitrary versions used in
consumer-policy unit fixtures. Keep declared minimums and lowest-test pins aligned; do not replace
generic tests whenever Popo's own dependencies change.

For automation changes, review triggers, token permissions, immutable action pins, required-check
names, artifact identity, and separation of validation from publication. Local tests do not prove
hosted environment or branch protections are active.

## Boundary Rules

Keep checks read-only and consumer policy explicit. Do not add placeholder services, speculative
plugin systems, or consumer-specific deployment assumptions simply to mirror another repository.
Define a demonstrated need, owner, public contract, failure behavior, and verification before adding
a new component.

Documentation work does not authorize implementation changes, external reruns, secret access, tag
creation, publication, or hosted-setting changes. Report discrepancies that require those actions
and obtain appropriate authorization. For release work, record exact candidate evidence through the
[release playbook]; preserve existing tags and report outstanding checks honestly.

[documentation synchronization guide]: ../../CONTRIBUTING.md#documentation-synchronization
[testing guide]: ../TESTING.md
[release playbook]: ../playbooks/release.md
[interface checklist]: https://github.com/Dagitali/engineering/blob/main/interfaces/evolution-checklist.md
