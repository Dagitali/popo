<!--
docs/hosted-audit.md
Popo hosted settings audit

Responsibilities
- Document explicit hosted expectations and limits of API evidence.

Maintainer Notes
- Preserve GET-only operation and separate absence from unavailable evidence.
-->

# Hosted Settings Audit

The opt-in `audit-github-settings` command compares configured expectations with GitHub API
observations. Public policy files do not establish enforcement. The command requires authenticated
`gh` access to github.com and is not included in `check-all`, tests, or ordinary `make check`. This
capability is unreleased; use the development checkout until a reviewed Popo release includes it.

- [Configuration](#configuration)
- [Evidence and Access](#evidence-and-access)
- [Approved Exceptions](#approved-exceptions)

## Configuration

Add explicit inventory to the consuming repository's pyproject.toml:

```toml
[tool.popo.hosted]
exceptions = []

[[tool.popo.hosted.repositories]]
name = "example/project"
codeowners = true
labels = ["bug", "enhancement"]
settings = { private-vulnerability-reporting = true, secret-scanning = true, secret-scanning-push-protection = true }
branches = { main = ["quality"] }
```

No organization, repository, branch, or check name is inferred. Omitted settings are not audited.
Each configured branch must report `protected: true`; configured check contexts must appear in
effective rules or legacy protection. Empty check arrays require only branch protection. Additional
required checks are allowed. Context matching is exact; source App identity is not validated.
Inventory is desired policy, not proof that owners have approved configuration changes.

```sh
popo audit-github-settings --root .
popo audit-github-settings --root . --format json
```

Reports go to stdout without creating files. JSON contains `observed_at` in UTC and narrow findings
with repository, check, status, detail, and evidence URL. Exit zero means all findings are verified
or excepted; exit one means missing settings, inaccessible evidence, expired exceptions, or invalid
configuration. Invalid configuration produces a JSON `error` when JSON is requested. Parser errors
retain argparse's exit two. Evidence URLs address mutable resources, not immutable snapshots.

## Evidence and Access

- `verified`: the requested observation matches; not proof of actual check execution or enforcement
  against every actor.
- `missing`: an observable setting differs, a label/file is absent, CODEOWNERS has hosted errors, or
  a required context is absent from fully available protection sources.
- `inaccessible`: authentication, permissions, rate limits, network/tool errors, ambiguous 404s,
  omitted security fields, malformed payloads, or truncated trees prevent a conclusion.
- `excepted`: confirmed drift has a configured, unexpired approval attestation.

The adapter uses only GET, bounds request time, and paginates label and effective-rule arrays. It
does not print tokens, raw responses, or arbitrary CLI errors. Repository metadata and branches must
be readable; 404 alone is not evidence of absence. A legacy protection response explicitly
identifying an unprotected branch is treated as absent legacy protection. CODEOWNERS existence is
checked on the default branch before using hosted validation errors; other branches are not checked.

Effective [branch rules] include active rules rather than mere policy declarations. The audit also
reads [legacy protection]. If either source is unavailable, absence is not assumed; a context
affirmatively present in readable effective rules can still be verified when legacy access fails.
Repository security fields may be omitted without administrative visibility. Use least-privilege
read permissions appropriate to the [repository API] and protection endpoints; never add write
permissions solely for this command.

This audit does not verify moderator/mailbox monitoring, personal notification preferences or
delivery, bypass actors, review-count policy, merge queue execution, check-source Apps, consumer
caller runs, or approval authenticity. Those require separately authorized evidence. It never
changes settings, installs tools, dispatches workflows, creates issues, or submits reports.

## Approved Exceptions

An exception is a reviewed attestation, not a mechanism for approving its own deviation:

```toml
[[tool.popo.hosted.exceptions]]
repository = "example/project"
check = "branch:main:check:quality"
owner = "responsible-maintainer"
reason = "Temporary migration; replacement check is tracked in the approval."
approved-by = "reviewing-maintainer"
approval = "https://github.com/example/project/issues/123"
expires = "2026-10-31"
```

Use only actual approval evidence. Check IDs are setting names, `label:NAME`, `codeowners`,
`branch:BRANCH:protected`, and `branch:BRANCH:check:CONTEXT`. Scope must match a configured
expectation; duplicates, unknown keys, malformed types, and incomplete approvals fail loading. Dates
must be quoted ISO dates. Expiry is inclusive through that UTC day; expired approvals always fail,
including when the original drift was corrected. Remove closed exceptions through review.
Inaccessible findings can never be excepted. The approval URL and approver are not authenticated by
this audit; repository review must establish their legitimacy. Do not put confidential approval
details or vulnerability reports into public configuration.

[legacy protection]: https://docs.github.com/en/rest/branches/branch-protection
[repository API]: https://docs.github.com/en/rest/repos/repos#get-a-repository
[branch rules]: https://docs.github.com/en/rest/repos/rules
