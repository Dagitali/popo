<!--
CHANGELOG.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Public history of user-visible changes and compatibility corrections.

Maintainer Notes
- Preserve released entries and group pending changes under Unreleased.
- Keep local links and documented behavior consistent with repository sources.
-->

# Changelog

All notable changes to this project will be documented in this file. Detailed release-candidate
records are indexed in the [release notes archive].

The format is based on [Keep a Changelog], and this project follows [Semantic Versioning].

- [Unreleased](#unreleased)
- [\[0.2.0\] - 2026-09-26](#020---2026-09-26)
- [\[0.1.5\] - 2026-09-24](#015---2026-09-24)
- [\[0.1.4\] - 2026-09-24](#014---2026-09-24)
- [\[0.1.3\] - 2026-09-24](#013---2026-09-24)
- [\[0.1.2\] - 2026-09-24](#012---2026-09-24)
- [\[0.1.1\] - 2026-09-24](#011---2026-09-24)
- [\[0.1.0\] - 2026-09-24](#010---2026-09-24)

## Unreleased

## [0.2.0] - 2026-09-26

Planned release; this preparation date does not establish tagging or publication.

- Exclude vendored `node_modules` Markdown from source discovery and match build exclusions by path
  component so maintained paths such as `docs/building.md` are no longer silently skipped.
- Reject local Markdown destinations that resolve outside the selected repository, including
  encoded parent paths and symlinked targets, while retaining valid in-repository parent links.
- Resolve block-list Python-version matrices in workflow policy checks alongside inline lists,
  validating each resolved version against the consumer's configured support range.
- Validate link fragments only for Markdown targets, avoiding decoding failures on binary files;
  reuse Markdown anchors within each check without retaining stale results between runs.
- Accept whitespace-delimited inline comments in dependency requirements and constraint files while
  preserving URL fragments and rejecting installer directives.
- Reject remote action references with a missing action name even when their revision is a full
  commit SHA; preserve local-action and container-reference exemptions.
- Validate Markdown reference-link destinations and explicit HTML anchors, including unused
  definitions; broken reference destinations now fail repository checks instead of being ignored.
- Accept plain links to existing directories without requiring a README; retain README anchor
  resolution for directory links with fragments.
- Ignore links and headings inside fenced Markdown code examples, including mixed or shorter
  embedded fence markers, while preserving source line numbers in real-link diagnostics.
- Run the existing local quality gate at the installed pre-push hook stage, using Make's interpreter
  selection rather than requiring a bare `python` executable.
- Describe the package without restricting consumer projects to Python and expose the maintained
  documentation URL in distribution metadata.
- Document the minimum-dependency fixture and shared formatting rules; ignore common
  operating-system metadata and additional coverage outputs without importing cloud-specific
  configuration.
- Expand the public README and documentation with configuration and testing references, onboarding
  and adoption tutorials, API and architecture guidance, release and change-management playbooks,
  incident and required-check runbooks, and reusable evidence and task templates.
- Raise development-tool minimum versions and align managed Ruff hooks with `ruff>=0.16.9,<0.17`;
  retain Python `>=3.13,<3.15` and the runtime dependency `packaging>=26.3,<27`.
- Expand checker regression coverage and public docstrings, and clarify the MIT terms in `NOTICE`
  without changing the license.

## [0.1.5] - 2026-09-24

- Remove `.github/README.md` so GitHub displays the root `README.md` as the repository homepage
  overview rather than the automation notes.
- Add the 0.1.5 release record and update the release archive.

## [0.1.4] - 2026-09-24

- Add the missing dated 0.1.3 changelog entry and prepare the 0.1.4 entry required by CD's
  release-changelog gate, without moving or reusing the existing 0.1.3 tag.
- Add the 0.1.4 release record and synchronize the release archive with the corrected history.

## [0.1.3] - 2026-09-24

- Update the Commitizen pre-commit hook from v4.18.0 to v4.18.1 and Ruff hooks from v0.16.7 to
  v0.16.8.
- This entry was added retrospectively in 0.1.4. The original 0.1.3 tagged tree lacked a dated
  changelog section, causing CD validation to fail; this correction does not change that tag.

## [0.1.2] - 2026-09-24

- Remove the obsolete Dependabot fixture-exclusion test that failed with `KeyError:
  'exclude-paths'`.
- Correct contributor and release guidance to allow Dependabot fixture updates while requiring
  matching metadata lower bounds before merging; retain the dependency-consistency check.
- Document release preparation and distinguish candidate validation from tagged artifact evidence.

## [0.1.1] - 2026-09-24

- Raise the minimum supported `packaging` version to 26.3 and synchronize the lowest-dependency
  test pin. Versions below 26.3 are no longer supported; the upper bound remains below 27.
- Add regression coverage for synchronized minimums, older and newer mismatched pins, and an
  intended Dependabot fixture exclusion. The missing configuration and obsolete exclusion test are
  addressed by 0.1.2.

## [0.1.0] - 2026-09-24

- Class-based pytest suites with reusable fixtures, independent installed-CLI scenarios, and
  expanded negative-path coverage for configuration, policy, and command dispatch.
- Scope-based test layers, shared artifact fixtures, automatic layer markers, and focused
  unit/integration Make targets; distribution validation remains opt-in.
- Explicit package discovery boundaries and shared pytest, Ruff, and coverage configuration
  conventions, including importlib-based test imports, retaining CLI-specific dependencies and test
  scope.
- Explicit virtual-environment creation, runtime/development installation, setup alias, and
  environment inspection targets that refuse to replace existing environments.
- Discoverable Make help, focused policy checks, common formatting/build/test aliases, and
  overridable tool, packaging, and distribution-test commands while preserving the existing local
  quality gate.
- Configurable PR routing, tagged release validation with opt-in GitHub publication, and manual
  cross-platform disposable installation workflows.
- Lowest/newest dependency CI, cross-platform distribution tests, and branch-coverage reporting.
- Standalone CycloneDX SBOM generation and manual runtime-dependency vulnerability auditing, with
  isolated tools, bounded permissions, and short-lived report artifacts.
- Explicit workflow schema comments and updated workflow responsibilities and boundaries.
- Generalized GitHub issue and pull request templates, file headers, dependency-update
  configuration, release-note templates, and portable contributor guidance.
- Shared Python setup action, bounded CI jobs, merge-group/manual validation, and full-history
  checkouts for Git-derived package versions.
- Editor and Git text conventions, issue and pull request templates, and opt-in pre-commit hooks
  adapted from `aws-cdk-static-site`.
- Checker regression cases and wheel/source-distribution contract and clean-install tests.
- Repository self-check and distribution validation Make targets, with artifact tests in CI.
- Initial `popo` command-line interface.
- Checks for Markdown links, GitHub Actions pins, dependency boundaries, Python-version policy, and
  release changelog entries.
- Declarative configuration through `[tool.popo]` in `pyproject.toml`.
- Pre-commit no longer requires a bare `python` on PATH: Popo checks use Make and filename-scoped
  Ruff hooks use a managed Python environment.
- Make selects the managed Python environment when no virtual environment is active, so local tests
  find the editable package without a `PYTHONPATH` workaround.
- Source tests and Make checks resolve the local `src` tree explicitly, including on macOS when
  hidden `.pth` files prevent editable-install path discovery.
- Complete the Python module rename to `popo` in packaging, development tooling, documentation, and
  clean-distribution tests.

[release notes archive]: docs/releases/README.md
[Keep a Changelog]: https://keepachangelog.com/en/1.1.0/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html
