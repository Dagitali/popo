<!--
REFERENCES.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Canonical repository sources and external format references.

Maintainer Notes
- Keep claims grounded in repository sources and preserve consumer-owned policy.
- Link to detailed guidance rather than maintaining competing copies.
-->

# References

Use executable sources for current behavior and maintained guides for interpretation. Historical
release records describe their own revisions, not the current checkout.

- [Package and Contributor Tooling](#package-and-contributor-tooling)
  - [Python Packaging and Testing](#python-packaging-and-testing)
- [Interfaces and Architecture](#interfaces-and-architecture)
- [Automation and Delivery](#automation-and-delivery)
- [Collaboration and Governance](#collaboration-and-governance)
- [External Formats](#external-formats)

## Package and Contributor Tooling

- [Package configuration]: Metadata, dependencies, supported Python, and tool settings.
- [Makefile]: Contributor commands and environment selection.
- [Contributing]: Setup, code style, checks, and documentation synchronization.
- [Test layout]: Test discovery, fixtures, and artifact boundaries.

### Python Packaging and Testing

The repository selects tool versions and settings in [Package configuration]. Consult upstream
documentation for tool behavior, then verify examples against the versions used here:

- [Python packaging guide]: `pyproject.toml` metadata and build configuration.
- [setuptools-scm]: Git-derived package versions.
- [pytest]: Test discovery, fixtures, and selection.
- [Ruff]: Linting and formatting.
- [mypy]: Static typing.
- [PEP 561]: Distributing type information and the `py.typed` marker.
- [pre-commit]: Managed hooks and stages.

These references supplement the local Make interface; they do not add mandatory commands,
dependencies, or external services.

## Interfaces and Architecture

- [Architecture]: Components, ownership, and execution flow.
- [Design]: Compatibility constraints and evolution rules.
- [Configuration]: Settings, defaults, input formats, and CLI boundaries.
- [API guidance]: Public interface and change review.
- [Learnings]: Reusable failures and verification paths.

## Automation and Delivery

- [Workflow map]: Triggers, roles, artifacts, and publication boundaries.
- [Branch protection]: Proposed hosted controls and configurable routing.
- [Release policy]: Tag validation, artifact identity, and optional publication.
- [Release archive]: Version-specific scope and recorded evidence.
- [GitHub Actions security]: Upstream guidance for reviewing workflow permissions and dependencies.
- [CycloneDX]: The dependency-inventory format used by SBOM automation.

## Collaboration and Governance

- [Agent instructions]: Repository-specific agent obligations.
- [Code of Conduct]: Participation and moderation.
- [Security]: Sensitive reports and validation limits.
- [Support]: Help channels and report contents.
- [Roadmap]: Readiness questions and future scope decisions.

## External Formats

- [CommonMark]: Baseline Markdown syntax.
- [GitHub Flavored Markdown]: GitHub's Markdown extensions.
- [TOML]: Syntax for package metadata and consumer configuration.
- [YAML]: Format specifications relevant to automation files.
- [Keep a Changelog]: Human-readable change history.
- [Semantic Versioning]: Version terminology and compatibility rules.

Format specifications do not imply complete parser support. Popo's [configuration] documents its
implemented subset and known limits.

[Branch protection]: .github/BRANCH-PROTECTION.md
[Agent instructions]: AGENTS.md
[Architecture]: ARCHITECTURE.md
[Workflow map]: CI-CD-WORKFLOWS.md
[Code of Conduct]: CODE_OF_CONDUCT.md
[Contributing]: CONTRIBUTING.md
[Design]: DESIGN.md
[Learnings]: LEARNINGS.md
[Makefile]: Makefile
[Release policy]: RELEASE-POLICY.md
[Roadmap]: ROADMAP.md
[Security]: SECURITY.md
[Support]: SUPPORT.md
[Configuration]: docs/CONFIGURATION.md
[API guidance]: docs/api/README.md
[Release archive]: docs/releases/README.md
[CycloneDX]: https://cyclonedx.org/specification/overview/
[Ruff]: https://docs.astral.sh/ruff/
[GitHub Actions security]: https://docs.github.com/en/actions/reference/security/secure-use
[pytest]: https://docs.pytest.org/
[GitHub Flavored Markdown]: https://github.github.com/gfm/
[Keep a Changelog]: https://keepachangelog.com/en/1.1.0/
[mypy]: https://mypy.readthedocs.io/
[Python packaging guide]: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
[PEP 561]: https://peps.python.org/pep-0561/
[pre-commit]: https://pre-commit.com/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html
[setuptools-scm]: https://setuptools-scm.readthedocs.io/
[CommonMark]: https://spec.commonmark.org/
[TOML]: https://toml.io/en/v1.0.0
[YAML]: https://yaml.org/spec/
[Package configuration]: pyproject.toml
[Test layout]: tests/README.md
