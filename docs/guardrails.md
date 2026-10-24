<!--
guardrails.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Language-neutral policy selection and literal local/CI invocation contracts.

Maintainer Notes
- Keep examples aligned with selection and guardrail validators.
- Separate static invocation evidence from execution and hosted enforcement.
-->

# Shared Local and CI Guardrails

Define a consumer-owned check profile once, invoke it through Make, and delegate the declared local
hook and CI step to that target. Popo inspects the wiring without executing consumer commands. This
works for Swift, Python, CDK and other repositories; Python remains Popo's execution runtime.

- [Consumer Policy](#consumer-policy)
- [Make Target](#make-target)
- [Pre-Commit Hook](#pre-commit-hook)
- [CI Step](#ci-step)
- [Inspection and Results](#inspection-and-results)
- [Boundaries](#boundaries)

## Consumer Policy

A Swift repository can use standalone `popo.toml` without creating `pyproject.toml`:

```toml
checks = ["check-guardrail-parity"]

[profiles.guardrails]
checks = ["check-docs", "check-required-files", "check-guardrail-parity"]

[files]
required = ["Package.swift", "README.md"]

[guardrails]
# Defaults select Makefile, .pre-commit-config.yaml and .github/workflows/ci.yml,
# target/profile/job "guardrails", and hook/step "popo".
```

For Python, place equivalent policy under `[tool.popo]`, `[tool.popo.profiles.guardrails]`,
`[tool.popo.files]` and `[tool.popo.guardrails]` in `pyproject.toml`. If `popo.toml` exists, it is
authoritative and does not merge Python metadata's policy. Python-specific checks still read their
configured package inputs. The [configuration reference] documents check selection and profiles.

CDK consumers can select these same language-neutral checks and require their own exact files, such
as `cdk.json`. Python CDK consumers may additionally select dependency and Python-policy checks.
This does not synthesize or inspect CDK applications, validate Swift manifests, or run language
tools.

## Make Target

Use a literal target with one recipe, selecting the profile explicitly. The recipe requires a tab:

```makefile
.PHONY: guardrails

guardrails:
	popo check-all --profile guardrails
```

An optional leading `@`, blank lines and non-recipe Make comments are accepted. Comments do not
terminate a recipe: additional tab-prefixed commands still fail validation. Variables,
prerequisites, extra commands and wrapper invocations are outside this deliberately literal recipe
contract. The profile includes the parity check so local hooks and CI check their own wiring as well
as the repository policies. This does not recurse: the parity checker reads the declarations without
invoking Make or running the profile again.

## Pre-Commit Hook

Use a local system hook so pre-commit delegates to the same Make target:

```yaml
repos:
  - repo: local
    hooks:
      - id: popo
        name: Repository guardrails
        entry: make guardrails
        language: system
        pass_filenames: false
        always_run: true
```

The configured hook ID must appear exactly once. Arguments cannot append another invocation or
change the profile. `always_run` and `pass_filenames` must be actual YAML booleans. Install the
selected Popo version and Make in the local environment; this checker does not install tools.

## CI Step

In `.github/workflows/ci.yml`, use the declared job and step IDs:

```yaml
jobs:
  guardrails:
    runs-on: ubuntu-latest
    steps:
      # Existing checkout and pinned Popo installation steps go here.
      - id: popo
        run: make guardrails
```

This is a job fragment, not a complete workflow. Consumers supply triggers, checkout, pinned tool
installation and appropriate permissions. The step must invoke exactly the same Make target and use
the repository root. Workflow/job run defaults selecting another working directory fail the
contract, even if overridden later; keep the declared wiring explicit.

## Inspection and Results

```console
popo explain --profile guardrails
popo check-all --profile guardrails
popo check-guardrail-parity
popo check-all --profile guardrails --format json
```

`explain` reports configuration provenance and selection without executing checks. `check-all`
without a profile uses the top-level selection, which inspects only parity in this example. Native
JSON results retain each check's public command name, pass/fail status and diagnostic messages; see
the [output contract]. A domain configuration failure does not hide later selected check results.

## Boundaries

The parity checker reads three declared files, safely parses YAML, and verifies literal commands. It
reports missing inputs, malformed YAML and invocation drift independently. It never runs Make,
hooks, workflow scripts or package manifests, installs tools, fetches code, or changes files.

A passing result establishes the declared invocation contract, not execution equivalence or hosted
enforcement. Make includes, conditionals and variable expansion; hook stages, environment overrides,
`SKIP` and exclusions; workflow triggers, conditions, dependencies and installed tool versions
remain outside this check. A workflow may not run even when its declared step passes inspection.
Validate actual local and hosted execution separately.

Named profiles are local policy selections. Shared remote policy bundles, workspace aggregation,
Swift/CDK semantic adapters, SARIF, toolchain reconciliation and generalized exceptions remain
future work; this foundation does not silently enable them.

[configuration reference]: CONFIGURATION.md#check-selection
[output contract]: CONFIGURATION.md#output-and-explanation
