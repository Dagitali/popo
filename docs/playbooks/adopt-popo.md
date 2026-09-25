<!--
adopt-popo.md
popo/docs/playbooks

Copyright © 2026 Dagitali LLC. All rights reserved.

Consumer-owned adoption of the CLI and migration from repository-local checks.

Maintainer Notes
- Preserve existing policy until behavioral differences are explicitly reviewed.
- Keep consumer setup and CI integration independent of language and cloud platform.
-->

# Adopt Popo in a Consumer Repository

Use this playbook to introduce selected checks or replace duplicated repository-local scripts. For a
first hands-on example, start with the [first-check tutorial]. Adoption does not require copying
Popo's Makefile, branching model, development dependencies, or workflows.

- [Choose the Adoption Path](#choose-the-adoption-path)
- [Prepare the Consumer](#prepare-the-consumer)
- [Capture the Existing Baseline](#capture-the-existing-baseline)
- [Integrate and Validate](#integrate-and-validate)
- [Retain Migration Safeguards](#retain-migration-safeguards)
- [Feed Evidence Back](#feed-evidence-back)

## Choose the Adoption Path

For a new repository, select checks that fit its actual files and policy. Do not create Python
package metadata merely to satisfy Python-specific checks in a non-Python project.

For an existing repository, treat replacement of local scripts as a behavior migration, not just an
invocation change. Inventory current inputs, exclusions, failure conditions, diagnostics, exit
statuses, callers, and required CI results before retiring anything.

## Prepare the Consumer

1. Follow the [installation instructions] and select a fixed reviewed Popo revision. Install through
   the consumer's reproducible tooling environment rather than relying on an adjacent checkout.
2. Provide an interpreter supported by Popo. The checked project's implementation language can
   differ; when running Python-policy checks, the interpreter must also satisfy the consumer policy.
3. Read the [configuration reference] and select commands individually. Documentation and action-pin
   checks do not require the consumer to adopt Popo's Python project conventions.
4. Keep build, deployment, credentials, dependency-update decisions, and CI ownership in the
   consumer. Record who approves policy changes and maintains the chosen tool revision.

`check-all` includes dependency and Python-policy validation; it is not a configurable subset of
checks. Release-changelog validation remains a separate command with an explicit version argument.

## Capture the Existing Baseline

Run the current scripts against the exact consumer revision being migrated. Record their commands,
interpreter, configuration, findings, and exit statuses without exposing private source or logs.
Include small positive and deliberately failing fixtures for each policy being replaced.

Compare Popo against those same inputs. Classify each mismatch as a configuration difference,
intentional policy change, unsupported behavior, or defect. For example, the current Markdown check
does not validate reference-link definitions, image links, or external URLs. Keep existing coverage
for requirements it does not implement; a passing Popo check is not proof of behavioral equivalence.

Separate adopting the tool from changing the consumer's policy wherever possible. Do not weaken
existing checks or copy Popo's own version constraints merely to make the migration pass.

## Integrate and Validate

Use the installed CLI with an explicit consumer root while comparing behavior. After substituting
the actual path, a documentation-only starting command is:

```console
python -m popo check-docs --root "/absolute/path/to/consumer"
```

Use the same selected commands locally and in CI, preserving their exit statuses. Run them after the
consumer checkout and tool installation. If individual path overrides are needed, check their
resolution rules in the configuration reference; not every relative path is based on `--root`.

Keep existing gates during comparison. Verify both known-good and known-bad inputs, then run the
consumer's normal quality gate. Only retire a local script after reviewing all of its callers and
confirming replacement coverage or retaining the unsupported portions. Do not copy Popo's entire
maintainer CI into the consumer as a shortcut.

When introducing or renaming required CI results, use the [required-check runbook] with the
consumer's actual branch policy. Editing workflow files alone does not configure hosted rules. This
playbook does not authorize changes to consumer repositories or external settings.

## Retain Migration Safeguards

Record the last known-good consumer revision, tool version, configuration, and invocation. Keep
regression fixtures for purposeful differences. If adoption fails, use a reviewed fix or revert that
restores compatible commands and policy; coordinate required-check names with any authorized
hosted-rule restoration. Do not bypass failed validation or move release tags to simplify recovery.

## Feed Evidence Back

Report reusable defects or requirements with minimal sanitized fixtures and expected behavior. Keep
consumer-specific policy outside the shared checker unless a reusable need is established. Use the
[interface checklist] for proposed CLI or configuration changes and the [incident runbook] for
unresolved failures. Consumer adoption alone is not evidence of support for every language,
platform, or policy.

[installation instructions]: ../../README.md#installation
[configuration reference]: ../CONFIGURATION.md
[interface checklist]: ../api/evolution-checklist.md
[incident runbook]: ../runbooks/incident-response.md
[required-check runbook]: ../runbooks/update-required-checks.md
[first-check tutorial]: ../tutorials/check-first-repository.md
