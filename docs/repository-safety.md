<!--
repository-safety.md
Read-only local safety policy

Maintainer Notes
- Keep generic checks separate from consumer policy and hosted evidence.
- Do not describe static checks as a sandbox or complete dependency audit.
-->

# Repository Safety

`popo check-repository-safety --root .` requires explicit `[tool.popo.safety]` configuration.
`check-all` includes it only when configured. This capability is unreleased; v0.5.2 does not provide
it. Checks read local files only, return one for failures, and never install packages, execute
workflow commands, or change settings. The [CLI guide] covers other checks.

- [Configuration](#configuration)
- [Workflow Trust Boundaries](#workflow-trust-boundaries)
- [npm Consistency](#npm-consistency)

## Configuration

```toml
[tool.popo.safety]
workflow-globs = [".github/workflows/*.yml"]
exceptions = []
npm-pairs = [
  { manifest = "source/package.json", lockfile = "locked/package-lock.json" },
  { manifest = "locked/package.json", lockfile = "locked/package-lock.json" },
]
```

All arrays default to empty. Every workflow pattern must match; include `.yaml`, templates, and
additional paths explicitly. Paths and resolved symlinks must remain inside the repository. Unknown
keys, malformed configuration, duplicate YAML keys, and unreadable inputs fail.

## Workflow Trust Boundaries

`pull_request_target` and `workflow_run` are denied by default because they can create privileged
execution boundaries. Allow only a reviewed workflow/trigger pair with a nonempty owner, reason,
approver, and quoted ISO expiry date:

```toml
[[tool.popo.safety.exceptions]]
workflow = ".github/workflows/triage.yml"
trigger = "pull_request_target"
owner = "responsible-maintainer"
reason = "Reviewed metadata-only triage; no untrusted checkout or artifacts executed"
approved-by = "independent-reviewer"
expires = "2026-11-07"
```

This is a schema example, not an approved exception. Exact paths only; duplicate scopes, expired
reviews, and unused exceptions fail. Approval authenticity is a review responsibility. Review
permissions, secrets, checkout refs, artifact trust, and every action's behavior before approving an
exception. Do not execute pull-request head code or untrusted artifacts in a privileged context.
Direct pull-request head references in `actions/checkout` also fail in privileged workflows, even
with an exception; indirect checkout and artifact flows still require review. Expiry uses the UTC
calendar date.

Direct `${{ github.event.pull_request... }}`, issue, comment, or discussion interpolation in `run`
commands fails even with an exception. Pass needed data through environment variables and quote
shell expansions. Caller-supplied reusable-workflow command inputs remain intentionally trusted and
are not prohibited. These bounded checks are not complete taint analysis: indirect expressions,
alternate event contexts, and third-party action behavior require review or a dedicated security
analyzer.

## npm Consistency

Each pair compares manifest name/version and dependency, development, and optional-dependency
specifications against the `packages[""]` root of an npm v2/v3 lockfile. Exact version pins also
require a matching top-level `node_modules` version. Configure both the committed manifest and any
source manifest copied into its directory by CI. This catches fixture drift without reimplementing
npm's resolver or implicitly updating a lockfile.

Ranges, peer resolution, workspaces, transitive graphs, and platform-specific optional packages are
not fully validated. Preserve `npm ci` and runtime fixture checks in hosted CI. A successful static
check does not prove installation or synthesis succeeds.

[CLI guide]: ../README.md
