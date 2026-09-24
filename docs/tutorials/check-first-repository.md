<!--
check-first-repository.md
popo/docs/tutorials

Copyright © 2026 Dagitali LLC. All rights reserved.

First consumer check with a deliberate Markdown failure and recovery.

Maintainer Notes
- Verify commands and output against the CLI and Markdown checker.
- Use disposable, reader-owned files; do not require Python project metadata.
-->

# Check a First Repository

This tutorial runs Popo against a small documentation folder. The consumer does not need to be a
Python project, use a cloud platform, or even have Git initialized. Popo itself needs a supported
Python interpreter. No credentials or deployment are involved.

- [Install Popo](#install-popo)
- [Prepare the Files](#prepare-the-files)
- [Run the Check](#run-the-check)
- [Observe and Fix a Failure](#observe-and-fix-a-failure)
- [Choose the Next Check](#choose-the-next-check)

## Install Popo

Use Python 3.13 or 3.14 in an isolated environment and follow the [installation instructions] to
install from a release tag or local checkout. Keep that environment active for the commands below.
Installation may access the network; the Markdown check only reads local files.

Confirm the selected interpreter can find Popo:

```console
python -m popo --version
python -m popo check-docs --help
```

## Prepare the Files

Create a new disposable folder using your editor or file manager. Add these two files:

- `README.md`: A heading and an inline Markdown link with label `Guide` and destination
  `guide.md#overview` (the usual bracketed label followed by a parenthesized destination).
- `guide.md`: A Markdown heading `# Overview` followed by a short paragraph.

Use an inline link for this exercise: the current checker does not validate reference-link
definitions or image links. A successful check also does not establish external URL availability or
the factual accuracy of the text.

## Run the Check

Replace `/absolute/path/to/consumer` with your new folder, keeping quotes around paths with spaces:

```console
python -m popo check-docs --root "/absolute/path/to/consumer"
```

Expect `PASS: local Markdown links are valid` and exit status `0`. The explicit root makes the
target independent of your shell's working directory. This command needs no `pyproject.toml` or
`[tool.popo]` settings and does not modify the files.

## Observe and Fix a Failure

Change the heading in `guide.md` from `# Overview` to `# Introduction`, leaving the link unchanged.
Run the same command again. Expect a `FAIL:` diagnostic containing the source file, line number, and
`anchor does not exist: guide.md#overview`, with exit status `1`.

Restore the heading or change the link destination to `guide.md#introduction`, then rerun the
command. Expect the original success message and exit status `0`. You made the repair; Popo only
reported and verified the mismatch. Keep this experiment out of real consumer files.

## Choose the Next Check

Use the [configuration reference] to choose checks that fit the consumer. For example, action-pin
validation is useful for a repository using GitHub Actions regardless of its implementation
language. Dependency and Python-policy checks have Python-specific inputs; `check-all` includes them
and is not an automatic next step for this documentation-only folder. Release-changelog validation
is separate and requires a release version.

Once a check works locally, run the same command in the consumer's existing CI after installing
Popo. Preserve its exit status so a reported failure fails the step; introducing CI is a separate
consumer-owned change. See the [incident runbook] for diagnosis and the [developer onboarding guide]
if you want to contribute to Popo itself.

[installation instructions]: ../../README.md#installation
[configuration reference]: ../CONFIGURATION.md
[developer onboarding guide]: ../development/onboarding.md
[incident runbook]: ../runbooks/incident-response.md
